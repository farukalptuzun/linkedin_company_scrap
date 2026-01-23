import re
import scrapy
from urllib.parse import quote_plus


class SectorBasedScraperSpider(scrapy.Spider):
    """
    Scrapes LinkedIn company profiles by first finding companies via a sector keyword search,
    then visiting each company profile and extracting profile details.
    """

    name = "sector_based_scraper"

    def __init__(self, sector: str = "", max_pages: str = "3", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sector = (sector or "").strip()
        if not self.sector:
            raise ValueError("sector is required. Example: scrapy crawl sector_based_scraper -a sector='Technology'")

        try:
            self.max_pages = max(1, int(max_pages))
        except Exception:
            self.max_pages = 3

        self._seen_company_urls: set[str] = set()

    def start_requests(self):
        # Try direct LinkedIn access first, fallback to Google Cache if needed
        encoded_sector = quote_plus(self.sector)
        search_url = f"https://www.linkedin.com/search/results/companies/?keywords={encoded_sector}"
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
            if company_url in self._seen_company_urls:
                continue
            self._seen_company_urls.add(company_url)
            yield scrapy.Request(
                url=company_url,
                callback=self.parse_company_profile,
                meta={"sector": self.sector, "company_url": company_url},
            )

        # Try pagination: LinkedIn typically supports `page=` in the query for some UIs.
        if page <= self.max_pages and normalized_urls:  # Only paginate if we found results
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
                next_search_url = f"{search_url}&start={start_param}"
                next_url = next_search_url
            
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

    def parse_company_profile(self, response):
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
        
        company_item = {}
        company_item["sector_query"] = response.meta.get("sector", self.sector)
        company_item["company_linkedin_url"] = response.meta.get("company_url", response.url)

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
        
        company_item["company_name"] = company_name or "not-found"

        # LinkedIn Followers Count - Multiple selectors (support Turkish "takipçi" too)
        followers_text = None
        followers_selectors = [
            '//p[contains(text(), "takipçi")]//text()',  # Turkish "takipçi"
            '//p[contains(text(), "followers")]//text()',  # English "followers"
            '//span[contains(text(), "takipçi")]//text()',
            '//span[contains(text(), "followers")]//text()',
            '//h3[contains(@class, "top-card-layout__first-subline")]/span/following-sibling::text()',
            '//span[contains(@class, "org-top-card-summary-info-list__item")]//text()[contains(., "followers")]',
            '.org-top-card-summary-info-list__item::text',
        ]
        for selector in followers_selectors:
            if selector.startswith('//'):
                texts = response.xpath(selector).getall()
                for text in texts:
                    if text and ('follower' in text.lower() or 'takipçi' in text.lower()):
                        followers_text = text
                        break
            else:
                texts = response.css(selector).getall()
                for text in texts:
                    if text and ('follower' in text.lower() or 'takipçi' in text.lower()):
                        followers_text = text
                        break
            if followers_text:
                break
        
        if followers_text:
            try:
                # Extract number from text like "140K followers", "1.2M followers", "140 B takipçi" (Turkish)
                # Handle Turkish format: "140 B takipçi" = 140 Billion
                followers_text_clean = followers_text.replace(',', '').replace('.', '')
                numbers = re.findall(r'(\d+)\s*([KMB]|Mn|B|Milyon)', followers_text_clean, re.IGNORECASE)
                if not numbers:
                    # Try simple number extraction
                    numbers = re.findall(r'[\d.]+[KMB]?', followers_text.replace(',', ''))
                
                if numbers:
                    if isinstance(numbers[0], tuple):
                        num_str = numbers[0][0]
                        unit = numbers[0][1].upper()
                    else:
                        num_str = numbers[0].upper()
                        unit = ''
                        if 'K' in num_str:
                            unit = 'K'
                            num_str = num_str.replace('K', '')
                        elif 'M' in num_str and 'MN' not in num_str.upper():
                            unit = 'M'
                            num_str = num_str.replace('M', '')
                        elif 'B' in num_str:
                            unit = 'B'
                            num_str = num_str.replace('B', '')
                    
                    num_value = float(num_str)
                    if unit == 'K' or unit == '':
                        company_item["linkedin_followers_count"] = int(num_value * 1000)
                    elif unit == 'M' or unit == 'MN' or 'milyon' in followers_text.lower():
                        company_item["linkedin_followers_count"] = int(num_value * 1000000)
                    elif unit == 'B' or 'b' in unit.lower():
                        company_item["linkedin_followers_count"] = int(num_value * 1000000000)
                    else:
                        company_item["linkedin_followers_count"] = int(num_value)
                else:
                    # Try to extract just numbers
                    num_match = re.search(r'(\d+[\d,\.]*)', followers_text.replace(',', ''))
                    if num_match:
                        company_item["linkedin_followers_count"] = int(float(num_match.group(1)))
                    else:
                        company_item["linkedin_followers_count"] = followers_text.strip()
            except Exception as e:
                self.logger.debug(f"Error parsing followers count: {e}")
                company_item["linkedin_followers_count"] = "not-found"
        else:
            company_item["linkedin_followers_count"] = "not-found"

        # Company Logo URL - Multiple selectors
        logo_url = None
        logo_selectors = [
            "div.top-card-layout__entity-image-container img::attr(data-delayed-url)",
            "div.top-card-layout__entity-image-container img::attr(src)",
            ".org-top-card-primary-content__logo img::attr(src)",
            ".org-top-card-primary-content__logo img::attr(data-delayed-url)",
            "img.org-top-card-primary-content__logo::attr(src)",
        ]
        for selector in logo_selectors:
            url = response.css(selector).get()
            if url and url.strip() and url != "not-found":
                logo_url = url.strip()
                break
        company_item["company_logo_url"] = logo_url or "not-found"

        # About Us - Multiple selectors (filter JSON data)
        about_text = None
        about_selectors = [
            ".core-section-container__content p::text",
            ".org-about-us-organization-description__text::text",
            ".break-words p::text",
            "section[data-test-id='about-us'] p::text",
            ".about-us__description p::text",
        ]
        for selector in about_selectors:
            texts = response.css(selector).getall()
            for text in texts:
                if text and text.strip() and len(text.strip()) > 10:
                    # Filter out JSON-like content
                    if '$recipeTypes' not in text and 'entityUrn' not in text and len(text.strip()) < 2000:
                        about_text = text.strip()
                        break
            if about_text:
                break
        
        # If single selector didn't work, try getting all paragraphs (filtered)
        if not about_text or about_text == "not-found":
            all_paragraphs = response.css(".core-section-container__content p::text").getall()
            if all_paragraphs:
                filtered_paragraphs = [
                    p.strip() for p in all_paragraphs 
                    if p.strip() and '$recipeTypes' not in p and 'entityUrn' not in p and len(p.strip()) < 2000
                ]
                if filtered_paragraphs:
                    about_text = " ".join(filtered_paragraphs[:3])  # Max 3 paragraphs
        
        company_item["about_us"] = about_text or "not-found"

        # Number of Employees - Multiple selectors
        employees = None
        employee_selectors = [
            "a.face-pile__cta::text",
            ".org-top-card-summary-info-list__item::text",
            '//span[contains(text(), "employees")]//text()',
            '//a[contains(@href, "employees")]//text()',
        ]
        for selector in employee_selectors:
            if selector.startswith('//'):
                raw = response.xpath(selector).get()
            else:
                raw = response.css(selector).get()
            if raw and 'employee' in raw.lower():
                employees = raw
                break
        
        if employees:
            try:
                match = re.findall(r"\d{1,3}(?:,\d{3})*(?:[KMB])?", employees.replace(',', ''))
                if match:
                    num_str = match[0].upper()
                    if 'K' in num_str:
                        company_item["num_of_employees"] = int(float(num_str.replace('K', '')) * 1000)
                    elif 'M' in num_str:
                        company_item["num_of_employees"] = int(float(num_str.replace('M', '')) * 1000000)
                    else:
                        company_item["num_of_employees"] = int(num_str.replace(',', ''))
                else:
                    company_item["num_of_employees"] = employees.strip()
            except Exception:
                company_item["num_of_employees"] = employees.strip()
        else:
            company_item["num_of_employees"] = "not-found"

        # Company Details Block - Modern LinkedIn structure
        try:
            # Website - More specific selectors
            website = None
            website_selectors = [
                ".org-top-card-summary-info-list__item a[href^='http']::attr(href)",
                ".core-section-container__content a[href^='http']::attr(href)",
                "a[data-test-id='website']::attr(href)",
            ]
            for selector in website_selectors:
                url = response.css(selector).get()
                if url and url.strip() and url.startswith('http') and 'linkedin.com' not in url:
                    website = url.strip()
                    break
            company_item["website"] = website or "not-found"

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
            # Industry
            industry_selectors = [
                ".org-top-card-summary-info-list__item:contains('Industry')::text",
                ".core-section-container__content:contains('Industry')::text",
            ]
            for selector in industry_selectors:
                try:
                    items = response.css(selector).getall()
                    for item in items:
                        if 'industry' in item.lower() and len(item.strip()) < 200:
                            industry = re.sub(r'Industry[:\s]*', '', item, flags=re.IGNORECASE).strip()
                            if industry and industry != "not-found":
                                break
                    if industry != "not-found":
                        break
                except:
                    pass
            
            # If not found, try regex on visible text (filtered)
            if industry == "not-found" and visible_text:
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
            
            company_item["industry"] = industry
            company_item["company_size_approx"] = company_size
            company_item["headquarters"] = headquarters
            company_item["type"] = company_type
            company_item["founded"] = founded
            company_item["specialties"] = specialties

            # Funding fields (best-effort)
            funding_text = response.css("p.text-display-lg::text").get()
            company_item["funding"] = funding_text.strip() if funding_text else "not-found"

            rounds_text = response.xpath(
                '//section[contains(@class, "aside-section-container")]/div/a[contains(@class, "link-styled")]//span[contains(@class, "before:middot")]/text()'
            ).get()
            if rounds_text:
                try:
                    company_item["funding_total_rounds"] = int(rounds_text.strip().split()[0])
                except Exception:
                    company_item["funding_total_rounds"] = rounds_text.strip()
            else:
                company_item["funding_total_rounds"] = "not-found"

            company_item["funding_option"] = response.xpath(
                '//section[contains(@class, "aside-section-container")]/div//div[contains(@class, "my-2")]/a[contains(@class, "link-styled")]/text()'
            ).get(default="not-found").strip()

            company_item["last_funding_round"] = response.xpath(
                '//section[contains(@class, "aside-section-container")]/div//div[contains(@class, "my-2")]/a[contains(@class, "link-styled")]//time[contains(@class, "before:middot")]/text()'
            ).get(default="not-found").strip()

        except Exception as e:
            self.logger.warning(f"Error parsing company details for {response.url}: {e}")
            # Keep partial item if the page layout differs.
            company_item.setdefault("website", "not-found")
            company_item.setdefault("industry", "not-found")
            company_item.setdefault("company_size_approx", "not-found")
            company_item.setdefault("headquarters", "not-found")
            company_item.setdefault("type", "not-found")
            company_item.setdefault("founded", "not-found")
            company_item.setdefault("specialties", "not-found")
            company_item.setdefault("funding", "not-found")
            company_item.setdefault("funding_total_rounds", "not-found")
            company_item.setdefault("funding_option", "not-found")
            company_item.setdefault("last_funding_round", "not-found")

        yield company_item

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

