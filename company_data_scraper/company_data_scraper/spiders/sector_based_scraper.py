import re
import scrapy
from urllib.parse import quote_plus, urljoin
from datetime import datetime
from company_data_scraper.items import LeadItem


class SectorBasedScraperSpider(scrapy.Spider):
    """
    Scrapes LinkedIn company profiles by first finding companies via a sector keyword search,
    then visiting each company profile and extracting profile details including contact information.
    """

    name = "sector_based_scraper"

    # Email regex pattern (matches most common email formats)
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    # Phone regex pattern (matches various phone formats)
    PHONE_PATTERN = re.compile(
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    )
    
    # Common contact/about page paths to check
    CONTACT_PATHS = [
        '/',
        '/contact',
        '/iletisim',
        '/about',
        '/hakkimizda',
        '/support',
        '/contacts',
        '/iletisim-bilgileri',
        '/contact-us',
        '/bize-ulasin',
    ]
    
    # Sector/Industry mapping for Turkish-English matching
    SECTOR_MAPPINGS = {
        'technology': ['technology', 'bilgi teknolojisi', 'bt', 'information technology', 'it', 
                      'bt hizmetleri', 'bilgi teknolojisi ve hizmetleri', 'information technology and services'],
        'bt': ['bt', 'bilgi teknolojisi', 'technology', 'information technology', 'it',
              'bt hizmetleri', 'bilgi teknolojisi ve hizmetleri'],
        'finance': ['finance', 'finans', 'financial services', 'finansal hizmetler'],
        'healthcare': ['healthcare', 'sağlık', 'health', 'sağlık hizmetleri'],
        'manufacturing': ['manufacturing', 'imalat', 'üretim'],
        'retail': ['retail', 'perakende', 'retail trade'],
        'education': ['education', 'eğitim', 'educational services'],
    }

    def __init__(self, sector: str = "", location: str = "", limit: str = "20", max_pages: str = "3", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sector = (sector or "").strip()
        self.location = (location or "").strip()
        
        if not self.sector:
            raise ValueError("sector is required. Example: scrapy crawl sector_based_scraper -a sector='Technology'")

        try:
            self.max_pages = max(1, int(max_pages))
        except Exception:
            self.max_pages = 3
            
        try:
            self.limit = max(1, int(limit))
        except Exception:
            self.limit = 20

        self._seen_company_urls: set[str] = set()
        self.processed_count = 0
        # Track companies being scraped (website -> company data)
        self.companies_in_progress = {}

    def start_requests(self):
        # Try direct LinkedIn access first, fallback to Google Cache if needed
        encoded_sector = quote_plus(self.sector)
        search_url = f"https://www.linkedin.com/search/results/companies/?keywords={encoded_sector}"
        
        # Add location to search URL if provided
        if self.location:
            encoded_location = quote_plus(self.location)
            search_url += f"&geoId=&location={encoded_location}"
        
        self.logger.info(f"🔍 Starting search: {search_url}")
        
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{search_url}"

        # Try direct LinkedIn first (better for JavaScript-rendered content)
        yield scrapy.Request(
            url=search_url,
            callback=self.parse_search_results,
            errback=self.errback_handler,
            meta={
                "page": 1,
                "search_url": search_url,
                "cache_url": cache_url,
                "use_cache": False
            },
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            dont_filter=True
        )

    def errback_handler(self, failure):
        # Fallback to Google Cache if direct LinkedIn fails
        self.logger.warning(f"Direct LinkedIn request failed: {failure.value}. Trying Google Cache...")
        request = failure.request
        cache_url = request.meta.get("cache_url")
        if cache_url:
            yield scrapy.Request(
                url=cache_url,
                callback=self.parse_search_results,
                meta={
                    "page": request.meta.get("page", 1),
                    "search_url": request.meta.get("search_url"),
                    "cache_url": cache_url,
                    "use_cache": True
                },
                dont_filter=True
            )

    def parse_search_results(self, response):
        page = int(response.meta.get("page", 1))
        search_url = response.meta.get("search_url")

        # Multiple strategies to extract company URLs from LinkedIn search results
        # Strategy 1: Try LinkedIn-specific CSS selectors for search results
        company_urls = []
        
        # Common LinkedIn search result selectors
        selectors = [
            'a[href*="/company/"]',  # Any link containing /company/
            '.search-result__info a[href*="/company/"]',  # Search result info links
            '.entity-result__title-text a[href*="/company/"]',  # Entity result title links
            '.search-result__result-link[href*="/company/"]',  # Search result links
            'div[data-chameleon-result-urn] a[href*="/company/"]',  # Result cards with URN
            'li[data-chameleon-result-urn] a[href*="/company/"]',  # List items with URN
            '.reusable-search__result-container a[href*="/company/"]',  # Reusable search results
            'a.app-aware-link[href*="/company/"]',  # App-aware links
            '[data-test-id="search-result"] a[href*="/company/"]',  # Test IDs
            '.search-result__wrapper a[href*="/company/"]',  # Search result wrapper
            '.entity-result a[href*="/company/"]',  # Entity result links
        ]
        
        for selector in selectors:
            links = response.css(f"{selector}::attr(href)").getall()
            if links:
                company_urls.extend(links)
                self.logger.info(f"Found {len(links)} company links using selector: {selector}")
        
        # Strategy 2: Fallback - extract all hrefs and filter
        if not company_urls:
            self.logger.warning("No company links found with specific selectors, trying fallback method")
            hrefs = response.css("a::attr(href)").getall()
            company_urls = self._extract_company_urls(hrefs)
        
        # Extract and normalize URLs
        normalized_urls = self._extract_company_urls(company_urls)
        
        self.logger.info(f"Page {page}: Found {len(normalized_urls)} unique company URLs")
        
        # If no URLs found, log the response for debugging
        if not normalized_urls:
            self.logger.warning(f"No company URLs found on page {page}. Response status: {response.status}")
            self.logger.debug(f"Response URL: {response.url}")
            self.logger.debug(f"Response body preview (first 500 chars): {response.text[:500]}")

        for company_url in normalized_urls:
            # Check limit before processing more companies
            if self.processed_count >= self.limit:
                self.logger.info(f"Reached limit of {self.limit} companies")
                return
            
            # Normalize URL for duplicate checking (remove /about/ suffix)
            # This ensures we don't process the same company twice
            base_url = company_url.rstrip('/').replace('/about', '')
            if base_url in self._seen_company_urls:
                self.logger.debug(f"Skipping duplicate URL: {base_url} (original: {company_url})")
                continue
            self._seen_company_urls.add(base_url)
            
            # Try to get the about page first (has more contact info)
            # Convert /company/name/ to /company/name/about/
            about_url = company_url
            if not company_url.endswith('/about/'):
                about_url = company_url.rstrip('/') + '/about/'
            
            self.logger.info(f"🔍 Requesting company profile: {about_url} (base: {base_url})")
            yield scrapy.Request(
                url=about_url,
                callback=self.parse_company_profile,
                meta={"sector": self.sector, "location": self.location, "company_url": base_url},
                errback=self.handle_company_profile_error,
            )

        # Try pagination: LinkedIn typically supports `page=` in the query for some UIs.
        # Only paginate if we haven't reached the limit and found results
        # Count how many new (non-duplicate) URLs were found
        new_urls_count = sum(1 for url in normalized_urls 
                            if url.rstrip('/').replace('/about', '') not in self._seen_company_urls)
        
        if page <= self.max_pages and self.processed_count < self.limit:
            # Continue pagination if:
            # 1. We found new URLs on this page, OR
            # 2. This is the first page (might have duplicates from previous runs)
            if new_urls_count > 0 or page == 1:
                next_page = page + 1
                use_cache = response.meta.get("use_cache", False)
                
                if use_cache:
                    # Use Google Cache for pagination
                    next_search_url = f"{search_url}&page={next_page}"
                    next_cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{next_search_url}"
                    next_url = next_cache_url
                else:
                    # Use direct LinkedIn URL for pagination
                    # LinkedIn uses start parameter for pagination: start=0, start=10, start=20, etc.
                    start_param = (next_page - 1) * 10
                    # LinkedIn typically shows 10 results per page
                    if '?' in search_url:
                        next_search_url = f"{search_url}&start={start_param}"
                    else:
                        next_search_url = f"{search_url}?start={start_param}"
                    next_url = next_search_url
                    self.logger.info(f"📄 Requesting page {next_page} (start={start_param}, found {new_urls_count} new URLs)")
                
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_search_results,
                    errback=self.errback_handler,
                    meta={
                        "page": next_page,
                        "search_url": search_url,
                        "cache_url": f"https://webcache.googleusercontent.com/search?q=cache:{search_url}&page={next_page}",
                        "use_cache": use_cache
                    },
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5", 
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    } if not use_cache else {},
                    dont_filter=True
                )
            else:
                self.logger.info(f"⏹️  Stopping pagination: No new URLs found on page {page} (all duplicates)")

    def parse_company_profile(self, response):
        self.logger.info(f"Parsing company profile: {response.url}")
        
        # Check limit before processing
        if self.processed_count >= self.limit:
            self.logger.info(f"Limit reached ({self.limit}), skipping: {response.url}")
            return
        
        # Login sayfası kontrolü - daha kapsamlı
        response_text_lower = response.text.lower() if response.text else ""
        if ('authwall' in response.url.lower() or 'login' in response.url.lower() or 
            'authwall' in response_text_lower or 'sign in' in response_text_lower[:2000] or
            'join linkedin' in response_text_lower[:2000]):
            self.logger.error(f"❌ Login sayfasına yönlendirildi: {response.url}")
            self.logger.error(f"💡 Cookie'ler expire olmuş olabilir. Cookie'leri yenileyin: python3 setup_linkedin_login.py")
            return
        
        # Sayfa içeriğinde login formu var mı kontrol et
        if (response.css('form[action*="login"]') or response.css('.authwall-sign-in-form') or
            response.css('#username') or response.css('#password')):
            self.logger.error(f"❌ Login formu tespit edildi: {response.url}")
            self.logger.error(f"💡 Cookie'leri yenileyin: python3 setup_linkedin_login.py")
            return
        
        sector = response.meta.get("sector", self.sector)
        location = response.meta.get("location", self.location)
        company_url = response.meta.get("company_url", response.url)

        # Company Name - Multiple fallback selectors for LinkedIn's different layouts
        company_name = None
        name_selectors = [
            ".top-card-layout__entity-info h1::text",
            "h1.org-top-card-summary__title::text",
            "h1.text-heading-xlarge::text",
            "h1[data-test-id='org-name']::text",
            "h1::text",
            ".org-top-card-summary-info__primary-text::text",
            "h1.top-card-layout__title::text",
        ]
        for selector in name_selectors:
            name = response.css(selector).get()
            if name and name.strip() and name.strip() != "not-found":
                company_name = name.strip()
                break
        
        company_name = company_name or None
        
        if not company_name or company_name == "not-found":
            self.logger.warning(f"Could not extract company name from {response.url}")
            self.logger.debug(f"Response status: {response.status}, URL: {response.url}")
            self.logger.debug(f"Response body preview (first 1000 chars): {response.text[:1000] if response.text else 'No text'}")
            return

        # Extract phone and email from LinkedIn profile (if available)
        phone_from_linkedin = None
        email_from_linkedin = None
        
        # Try to find phone/email in LinkedIn profile
        # Check both main page and about page structure
        phone_selectors = [
            'a[href^="tel:"]::attr(href)',  # tel:+902162322230
            'a[href^="tel:"] span::text',   # Text inside tel: link
            'dd a[href^="tel:"]::attr(href)',  # About page structure
            'dd a[href^="tel:"] span::text',
            '.org-top-card-summary-info-list__item:contains("phone")::text',
            '.org-top-card-summary-info-list__item:contains("Phone")::text',
        ]
        for selector in phone_selectors:
            phone_text = response.css(selector).get()
            if phone_text:
                # Remove tel: prefix if present
                phone_text = phone_text.replace('tel:', '').strip()
                # Extract phone from tel: link or text
                phone_match = self.PHONE_PATTERN.search(phone_text)
                if phone_match:
                    phone_from_linkedin = phone_match.group(0)
                    self.logger.info(f"✅ Found phone on LinkedIn: {phone_from_linkedin}")
                break
        
        email_selectors = [
            'a[href^="mailto:"]::attr(href)',
            'a[href^="mailto:"]::text',
            'dd a[href^="mailto:"]::attr(href)',  # About page structure
            'dd a[href^="mailto:"] span::text',
            '.org-top-card-summary-info-list__item:contains("@")::text',
        ]
        for selector in email_selectors:
            email_text = response.css(selector).get()
            if email_text:
                # Extract email from mailto: link or text
                if email_text.startswith('mailto:'):
                    email_from_linkedin = email_text.replace('mailto:', '').strip()
                else:
                    email_match = self.EMAIL_PATTERN.search(email_text)
                    if email_match:
                        email_from_linkedin = email_match.group(0)
                if email_from_linkedin:
                    self.logger.info(f"✅ Found email on LinkedIn: {email_from_linkedin}")
                    break

        # Company Details Block - Modern LinkedIn structure
        website = None
        visible_text = ""  # Initialize for use in sector filtering
        try:
            # Website - More specific selectors including About page structure
            website_selectors = [
                "dd a[href^='http']::attr(href)",  # About page: <dd><a href="https://...">
                ".org-top-card-summary-info-list__item a[href^='http']::attr(href)",
                ".core-section-container__content a[href^='http']::attr(href)",
                "a[data-test-id='website']::attr(href)",
            ]
            for selector in website_selectors:
                url = response.css(selector).get()
                if url and url.strip() and url.startswith('http') and 'linkedin.com' not in url:
                    website = url.strip()
                    self.logger.info(f"✅ Found website: {website}")
                    break

            # Industry, Size, Headquarters, Type, Founded, Specialties
            # Use more specific selectors to avoid JSON data
            industry = "not-found"
            company_size = "not-found"
            headquarters = "not-found"
            company_type = "not-found"
            founded = "not-found"
            specialties = "not-found"
            
            # Try to get visible text only (exclude script tags and JSON)
            # Get all visible text from the main content area
            visible_text_elements = response.css("body *:not(script):not(style)::text").getall()
            visible_text = " ".join([t.strip() for t in visible_text_elements if t.strip() and len(t.strip()) < 500])
            
            # More specific selectors for LinkedIn's current structure
            # Industry (Sektör) - Check both English and Turkish
            industry_selectors = [
                "dt:contains('Sektör') + dd::text",  # Turkish: "Sektör"
                "dt:contains('Industry') + dd::text",  # English: "Industry"
                ".org-top-card-summary-info-list__item:contains('Sektör')::text",
                ".org-top-card-summary-info-list__item:contains('Industry')::text",
                ".core-section-container__content:contains('Industry')::text",
            ]
            for selector in industry_selectors:
                try:
                    items = response.css(selector).getall()
                    for item in items:
                        if item and item.strip():
                            # Remove labels like "Sektör:", "Industry:"
                            industry_text = re.sub(r'(Sektör|Industry)[:\s]*', '', item, flags=re.IGNORECASE).strip()
                            if industry_text and len(industry_text) < 200 and industry_text != "not-found":
                                # Filter out JSON-like content
                                if '$recipeTypes' not in industry_text and 'entityUrn' not in industry_text:
                                    industry = industry_text
                                break
                    if industry != "not-found":
                        break
                except:
                    pass
            
            # If not found, try regex on visible text (filtered)
            if industry == "not-found" and visible_text:
                # Try Turkish first
                industry_match = re.search(r'Sektör[:\s]+([^\n<]{1,100})', visible_text, re.IGNORECASE)
                if not industry_match:
                    # Try English
                    industry_match = re.search(r'Industry[:\s]+([^\n<]{1,100})', visible_text, re.IGNORECASE)
                if industry_match:
                    industry = industry_match.group(1).strip()
                    # Filter out JSON-like content
                    if '$recipeTypes' in industry or 'entityUrn' in industry:
                        industry = "not-found"
            
            # Company Size
            size_selectors = [
                ".org-top-card-summary-info-list__item:contains('employees')::text",
                ".org-top-card-summary-info-list__item:contains('Company size')::text",
            ]
            for selector in size_selectors:
                try:
                    items = response.css(selector).getall()
                    for item in items:
                        if ('employee' in item.lower() or 'company size' in item.lower()) and len(item.strip()) < 200:
                            size_match = re.search(r'(\d+[KMB]?|\d+,\d+)', item, re.IGNORECASE)
                            if size_match:
                                company_size = size_match.group(0)
                                break
                    if company_size != "not-found":
                        break
                except:
                    pass
            
            # Headquarters
            hq_selectors = [
                ".org-top-card-summary-info-list__item:contains('Headquarters')::text",
                ".core-section-container__content:contains('Headquarters')::text",
            ]
            for selector in hq_selectors:
                try:
                    items = response.css(selector).getall()
                    for item in items:
                        if 'headquarters' in item.lower() and len(item.strip()) < 200:
                            headquarters = re.sub(r'Headquarters[:\s]*', '', item, flags=re.IGNORECASE).strip()
                            if headquarters and headquarters != "not-found":
                                break
                    if headquarters != "not-found":
                        break
                except:
                    pass
            
            if headquarters == "not-found" and visible_text:
                hq_match = re.search(r'Headquarters[:\s]+([^\n<]{1,100})', visible_text, re.IGNORECASE)
                if hq_match:
                    headquarters = hq_match.group(1).strip()
                    if '$recipeTypes' in headquarters or 'entityUrn' in headquarters:
                        headquarters = "not-found"
            
            # Type
            if visible_text:
                type_match = re.search(r'Type[:\s]+([^\n<]{1,100})', visible_text, re.IGNORECASE)
                if type_match:
                    company_type = type_match.group(1).strip()
                    if '$recipeTypes' in company_type or 'entityUrn' in company_type:
                        company_type = "not-found"
            
            # Founded
            if visible_text:
                founded_match = re.search(r'Founded[:\s]+([^\n<]{1,100})', visible_text, re.IGNORECASE)
                if founded_match:
                    founded = founded_match.group(1).strip()
                    if '$recipeTypes' in founded or 'entityUrn' in founded:
                        founded = "not-found"
            
            # Specialties
            if visible_text:
                specialties_match = re.search(r'Specialties[:\s]+([^\n<]{1,200})', visible_text, re.IGNORECASE)
                if specialties_match:
                    specialties = specialties_match.group(1).strip()
                    if '$recipeTypes' in specialties or 'entityUrn' in specialties:
                        specialties = "not-found"

        except Exception as e:
            self.logger.warning(f"Error parsing company details for {response.url}: {e}")
        
        # Filter by sector/industry match - TEMPORARILY DISABLED FOR TESTING
        # TODO: Re-enable sector filtering after testing
        if False:  # Temporarily disabled
            # Normalize both the requested sector and found industry for comparison
            if industry != "not-found" and self.sector:
                # Normalize: lowercase, remove extra spaces
                requested_sector_normalized = self.sector.lower().strip()
                found_industry_normalized = industry.lower().strip()
                
                # Get all possible keywords for the requested sector
                sector_keywords = [requested_sector_normalized]
                
                # Add mapped keywords if sector has a mapping
                if requested_sector_normalized in self.SECTOR_MAPPINGS:
                    sector_keywords.extend(self.SECTOR_MAPPINGS[requested_sector_normalized])
                else:
                    # Try to find partial match in mappings
                    for key, values in self.SECTOR_MAPPINGS.items():
                        if requested_sector_normalized in values or any(
                            req_word in key or req_word in values 
                            for req_word in requested_sector_normalized.split()
                        ):
                            sector_keywords.extend(values)
                            break
                
                # Also add individual words from requested sector
                sector_keywords.extend(requested_sector_normalized.split())
                
                # Remove duplicates and filter short words
                sector_keywords = list(set([kw for kw in sector_keywords if len(kw) > 2]))
                
                # Check if any keyword matches the found industry
                matches = (
                    requested_sector_normalized in found_industry_normalized or
                    found_industry_normalized in requested_sector_normalized or
                    any(keyword in found_industry_normalized for keyword in sector_keywords)
                )
                
                if not matches:
                    self.logger.info(f"⏭️  Skipping {company_name}: Industry '{industry}' doesn't match requested sector '{self.sector}'")
                    self.logger.debug(f"   Requested keywords: {sector_keywords}")
                    return  # Skip this company
                else:
                    self.logger.info(f"✅ Industry match: '{industry}' matches requested sector '{self.sector}'")
            elif industry == "not-found":
                # Industry bulunamadı, ama şirket isminde veya açıklamasında sektör var mı kontrol et
                # Get all possible keywords for the requested sector
                requested_sector_normalized = self.sector.lower().strip()
                sector_keywords = [requested_sector_normalized]
                
                # Add mapped keywords if sector has a mapping
                if requested_sector_normalized in self.SECTOR_MAPPINGS:
                    sector_keywords.extend(self.SECTOR_MAPPINGS[requested_sector_normalized])
                else:
                    # Try to find partial match in mappings
                    for key, values in self.SECTOR_MAPPINGS.items():
                        if requested_sector_normalized in values or any(
                            req_word in key or req_word in values 
                            for req_word in requested_sector_normalized.split()
                        ):
                            sector_keywords.extend(values)
                            break
                
                # Also add individual words from requested sector
                sector_keywords.extend(requested_sector_normalized.split())
                sector_keywords = list(set([kw for kw in sector_keywords if len(kw) > 2]))
                
                # Check company name and visible text for sector keywords
                # Use response.text as fallback if visible_text is empty
                searchable_text = visible_text if visible_text else (response.text[:5000].lower() if response.text else "")
                company_text = f"{company_name} {searchable_text}".lower()
                if any(keyword in company_text for keyword in sector_keywords):
                    self.logger.info(f"⚠️  Industry not found but sector keywords found in company info, proceeding")
                else:
                    self.logger.warning(f"⚠️  Could not extract industry for {company_name} and no sector keywords found, skipping")
                    return
        
        # Log industry info for debugging (even when filtering is disabled)
        if industry != "not-found":
            self.logger.debug(f"📊 {company_name}: Industry='{industry}' (filtering disabled)")
        else:
            self.logger.debug(f"📊 {company_name}: Industry not found (filtering disabled, proceeding)")
        
        # If we have phone/email from LinkedIn, use them; otherwise scrape website
        if phone_from_linkedin or email_from_linkedin:
            # We have contact info from LinkedIn, create item directly
            emails_list = [email_from_linkedin] if email_from_linkedin else []
            item = LeadItem(
                sector=sector,
                location=location,
                company_name=company_name,
                phone=phone_from_linkedin or "",
                emails=emails_list,
                website=website or None,
                source='linkedin',
                created_at=datetime.utcnow(),
            )
            self.processed_count += 1
            self.logger.info(f"[{self.processed_count}/{self.limit}] Found contact info on LinkedIn: {company_name}")
            yield item
        elif website and website != "not-found":
            # No contact info on LinkedIn, scrape website
            # Normalize website URL
            if not website.startswith('http'):
                website = 'https://' + website
            
            # Initialize tracking for this company
            company_key = website
            self.companies_in_progress[company_key] = {
                'company_name': company_name,
                'phone': phone_from_linkedin or "",
                'website': website,
                'emails': set([email_from_linkedin] if email_from_linkedin else []),
                'pages_processed': 0,
                'total_pages': len(self.CONTACT_PATHS),
                'sector': sector,
                'location': location,
            }
            
            # Request multiple pages from the website
            for path in self.CONTACT_PATHS:
                url = urljoin(website, path)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_website_for_contacts,
                    meta={
                        'company_key': company_key,
                        'dont_redirect': True,
                    },
                    errback=self.handle_website_error,
                    dont_filter=False,
                )
        else:
            # No website, yield item with empty contact info
            item = LeadItem(
                sector=sector,
                location=location,
                company_name=company_name,
                phone=phone_from_linkedin or "",
                emails=[email_from_linkedin] if email_from_linkedin else [],
                website=None,
                source='linkedin',
                created_at=datetime.utcnow(),
            )
            self.processed_count += 1
            self.logger.info(f"[{self.processed_count}/{self.limit}] No website found: {company_name}")
            yield item

    def parse_website_for_contacts(self, response):
        """Extract emails and phone numbers from website pages"""
        company_key = response.meta.get('company_key')
        
        if company_key not in self.companies_in_progress:
            self.logger.warning(f"Company key {company_key} not found in tracking")
            return
        
        company_data = self.companies_in_progress[company_key]
        company_data['pages_processed'] += 1
        
        # Extract emails from page text
        page_text = response.text
        emails_found = set(self.EMAIL_PATTERN.findall(page_text))
        
        # Normalize emails (lowercase)
        emails_found = {email.lower() for email in emails_found}
        
        # Filter out common non-email patterns (like image URLs, CSS, JS)
        emails_found = {
            email for email in emails_found
            if not email.startswith('//') and '@' in email
            and not email.endswith('.png') and not email.endswith('.jpg')
            and not email.endswith('.gif') and not email.endswith('.css')
            and not email.endswith('.js')
        }
        
        if emails_found:
            self.logger.info(f"Found {len(emails_found)} emails on {response.url}")
            company_data['emails'].update(emails_found)
        
        # Extract phone numbers from page text
        phones_found = self.PHONE_PATTERN.findall(page_text)
        if phones_found and not company_data['phone']:
            # Use the first valid phone number found
            for phone in phones_found:
                # Clean up phone number
                phone_clean = re.sub(r'[^\d+\-().\s]', '', phone).strip()
                if len(phone_clean) >= 10:  # Minimum phone number length
                    company_data['phone'] = phone_clean
                    self.logger.info(f"Found phone number on {response.url}: {phone_clean}")
                    break
        
        # Check if all pages have been processed
        if company_data['pages_processed'] >= company_data['total_pages']:
            # All pages processed, yield final item
            item = LeadItem(
                sector=company_data['sector'],
                location=company_data['location'],
                company_name=company_data['company_name'],
                phone=company_data['phone'],
                emails=list(company_data['emails']),
                website=company_data['website'],
                source='linkedin',
                created_at=datetime.utcnow(),
            )
            self.processed_count += 1
            self.logger.info(
                f"[{self.processed_count}/{self.limit}] Completed scraping {company_data['company_name']}: "
                f"{len(company_data['emails'])} emails, phone: {'Yes' if company_data['phone'] else 'No'}"
            )
            # Remove from tracking
            del self.companies_in_progress[company_key]
            yield item
    
    def handle_company_profile_error(self, failure):
        """Handle errors when scraping company profile pages"""
        company_url = failure.request.meta.get('company_url', failure.request.url)
        self.logger.error(f"Failed to scrape company profile {company_url}: {failure.value}")
        self.logger.debug(f"Request URL: {failure.request.url}")
        if hasattr(failure.value, 'response') and failure.value.response:
            self.logger.debug(f"Response status: {failure.value.response.status}")
    
    def handle_website_error(self, failure):
        """Handle errors when scraping website pages"""
        company_key = failure.request.meta.get('company_key')
        
        if company_key not in self.companies_in_progress:
            return
        
        company_data = self.companies_in_progress[company_key]
        company_data['pages_processed'] += 1
        
        self.logger.warning(f"Failed to scrape {failure.request.url}: {failure.value}")
        
        # Check if all pages have been processed (including errors)
        if company_data['pages_processed'] >= company_data['total_pages']:
            # All pages processed (with some errors), yield item with what we have
            item = LeadItem(
                sector=company_data['sector'],
                location=company_data['location'],
                company_name=company_data['company_name'],
                phone=company_data['phone'],
                emails=list(company_data['emails']),
                website=company_data['website'],
                source='linkedin',
                created_at=datetime.utcnow(),
            )
            self.processed_count += 1
            self.logger.info(
                f"[{self.processed_count}/{self.limit}] Completed scraping {company_data['company_name']} "
                f"(with some errors): {len(company_data['emails'])} emails, phone: {'Yes' if company_data['phone'] else 'No'}"
            )
            # Remove from tracking
            del self.companies_in_progress[company_key]
            yield item

    @staticmethod
    def _extract_company_urls(hrefs: list[str]) -> list[str]:
        out: list[str] = []
        for href in hrefs:
            if not href:
                continue
            
            # Handle Google Cache URLs that wrap LinkedIn URLs
            if "webcache.googleusercontent.com" in href and "linkedin.com/company/" in href:
                # Extract LinkedIn URL from cache URL query parameter
                cache_match = re.search(r"cache:(https?://[^&]+)", href)
                if cache_match:
                    href = cache_match.group(1)
                # Or extract from URL-encoded form
                if "linkedin.com/company/" in href:
                    url_match = re.search(r"(https?://[^&]*linkedin\.com/company/[^&\"'#]+)", href)
                    if url_match:
                        href = url_match.group(1)
            
            # Skip if not a company URL
            if "linkedin.com/company/" not in href.lower():
                continue
            
            # Extract clean LinkedIn company URL
            # Pattern 1: Full URL with https://
            m = re.search(r"(https?://(?:www\.)?linkedin\.com/company/[^/?\"'#\s]+)", href, re.IGNORECASE)
            if m:
                clean_url = m.group(1).rstrip('/')
                # Remove common tracking parameters
                clean_url = re.sub(r'[?&](trk|original_referer|originalSubdomain)=[^&]*', '', clean_url)
                out.append(clean_url)
            else:
                # Pattern 2: Relative URL starting with /company/
                if href.startswith("/company/") or "/company/" in href:
                    rel_match = re.search(r"(/company/[^/?\"'#\s]+)", href)
                    if rel_match:
                        clean_url = "https://www.linkedin.com" + rel_match.group(1).rstrip('/')
                        out.append(clean_url)
        
        # De-dupe, keep order
        seen = set()
        unique = []
        for u in out:
            # Normalize URL (lowercase domain, remove trailing slash)
            normalized = u.lower().rstrip('/')
            if normalized not in seen and normalized:
                seen.add(normalized)
                unique.append(u)  # Keep original case for the URL path
        return unique

