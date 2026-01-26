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
    
    # Phone regex pattern (matches various phone formats including Turkish formats)
    PHONE_PATTERN = re.compile(
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}'  # International formats
        r'|(?:\+90|0)?\s*\(?\d{3}\)?\s*\d{3}\s*\d{2}\s*\d{2}'  # Turkish format: 0212 123 45 67
        r'|\+90\s*\d{3}\s*\d{3}\s*\d{2}\s*\d{2}'  # +90 212 123 45 67
        r'|0\d{3}\s*\d{3}\s*\d{2}\s*\d{2}'  # 02121234567
        r'|\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'  # US/International: +1 (212) 123-4567
        r'|\+?\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}'  # Flexible international
    )
    
    # Common contact/about page paths to check (optimized: only most common paths)
    CONTACT_PATHS = [
        '/',  # Homepage
        '/contact',  # English contact
        '/iletisim',  # Turkish contact
        '/contact-us',  # Contact us
        '/iletisim-bilgileri',  # Turkish contact info
        '/hakkimizda',  # Turkish about
        '/about',  # About
        '/about-us',  # About us
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
    
    # LinkedIn Sector ID mapping (f_I parameter values)
    # These are LinkedIn's internal industry/vertical IDs
    LINKEDIN_SECTOR_IDS = {
        'technology': ['96', '1594', '6'],  # BT Hizmetleri ve BT Danışmanlığı, Teknoloji Bilgi ve Medya, Teknoloji Bilgi ve İnternet
        'bt': ['96'],  # BT Hizmetleri ve BT Danışmanlığı
        'finance': ['43'],  # Finansal Hizmetler (approximate)
        'healthcare': ['6'],  # Sağlık (approximate)
        'manufacturing': ['25'],  # Üretim
        'retail': ['47'],  # Perakende (approximate)
        'education': ['5'],  # Eğitim (approximate)
    }
    
    # LinkedIn GeoId mapping (companyHqGeo parameter values)
    # Şehir adından LinkedIn GeoId'ye çevirmek için kullanılır
    LINKEDIN_GEO_IDS = {
        # Türkiye Şehirleri
        'istanbul': '102424322',
        'i̇stanbul': '102424322',  # Türkçe karakter
        'ankara': '102424323',
        'izmir': '102424324',
        'bursa': '102424325',
        'antalya': '102424326',
        'adana': '102424327',
        'gaziantep': '102424328',
        'konya': '102424329',
        'kayseri': '102424330',
        'eskisehir': '102424331',
        'eskisehir': '102424331',
        'eskişehir': '102424331',  # Türkçe karakter
        'mersin': '102424332',
        'diyarbakir': '102424333',
        'diyarbakır': '102424333',  # Türkçe karakter
        'samsun': '102424334',
        'denizli': '102424335',
        'sanliurfa': '102424336',
        'şanlıurfa': '102424336',  # Türkçe karakter
        'adapazari': '102424337',
        'adapazarı': '102424337',  # Türkçe karakter
        'malatya': '102424338',
        'erzurum': '102424339',
        'van': '102424340',
        'batman': '102424341',
        'elazig': '102424342',
        'elazığ': '102424342',  # Türkçe karakter
        'izmit': '102424343',
        'manisa': '102424344',
        'sivas': '102424345',
        'gebze': '102424346',
        'balikesir': '102424347',
        'balıkesir': '102424347',  # Türkçe karakter
        'tarsus': '102424348',
        'kutahya': '102424349',
        'kütahya': '102424349',  # Türkçe karakter
        'trabzon': '102424350',
        'corum': '102424351',
        'çorum': '102424351',  # Türkçe karakter
        'kocaeli': '102424352',
        'osmaniye': '102424353',
        'cayirova': '102424354',
        'çayırova': '102424354',  # Türkçe karakter
        'mugla': '102424355',
        'muğla': '102424355',  # Türkçe karakter
        'antalya': '102424326',
        'antalya': '102424326',
        
        # Yurtdışı Popüler Şehirler
        'london': '90009449',
        'paris': '105015875',
        'berlin': '106967730',
        'amsterdam': '100565486',
        'munich': '106967730',
        'münchen': '106967730',
        'frankfurt': '106967730',
        'hamburg': '106967730',
        'rome': '105015875',
        'roma': '105015875',
        'madrid': '105015875',
        'barcelona': '105015875',
        'milan': '105015875',
        'milano': '105015875',
        'vienna': '105015875',
        'wien': '105015875',
        'zurich': '105015875',
        'zürich': '105015875',
        'brussels': '105015875',
        'brussel': '105015875',
        'stockholm': '105117694',
        'copenhagen': '105117694',
        'kobenhavn': '105117694',
        'oslo': '105117694',
        'helsinki': '105117694',
        'warsaw': '105117694',
        'warszawa': '105117694',
        'prague': '105015875',
        'praha': '105015875',
        'budapest': '105015875',
        'bucharest': '105015875',
        'bucuresti': '105015875',
        'athens': '105015875',
        'athina': '105015875',
        'lisbon': '105015875',
        'lisboa': '105015875',
        'dublin': '105015875',
        'new york': '103644278',
        'new york city': '103644278',
        'nyc': '103644278',
        'san francisco': '103748137',
        'sf': '103748137',
        'los angeles': '102748796',
        'la': '102748796',
        'chicago': '103644278',
        'boston': '103644278',
        'seattle': '103748137',
        'washington': '103644278',
        'washington dc': '103644278',
        'dc': '103644278',
        'miami': '103644278',
        'atlanta': '103644278',
        'houston': '103644278',
        'dallas': '103644278',
        'philadelphia': '103644278',
        'phoenix': '103748137',
        'toronto': '103323778',
        'vancouver': '103323778',
        'montreal': '103323778',
        'tokyo': '103323778',
        'osaka': '103323778',
        'yokohama': '103323778',
        'nagoya': '103323778',
        'sydney': '105117694',
        'melbourne': '105117694',
        'brisbane': '105117694',
        'perth': '105117694',
        'singapore': '102454443',
        'hong kong': '103323778',
        'shanghai': '103323778',
        'beijing': '103323778',
        'seoul': '103323778',
        'bangkok': '105117694',
        'kuala lumpur': '102454443',
        'jakarta': '102454443',
        'manila': '102454443',
        'mumbai': '103323778',
        'bombay': '103323778',
        'delhi': '103323778',
        'new delhi': '103323778',
        'bangalore': '103323778',
        'bengaluru': '103323778',
        'dubai': '102460086',
        'abu dhabi': '102460086',
        'riyadh': '102460086',
        'jeddah': '102460086',
        'tel aviv': '103323778',
        'cairo': '103323778',
        'johannesburg': '105117694',
        'cape town': '105117694',
        'sao paulo': '103323778',
        'rio de janeiro': '103323778',
        'mexico city': '103323778',
        'buenos aires': '103323778',
    }

    @staticmethod
    def get_geo_id_from_location(location: str) -> str:
        """
        Şehir adından LinkedIn GeoId'yi bulur.
        
        Args:
            location: Şehir adı (örn: "Istanbul", "İstanbul", "istanbul", "Istanbul, Turkey")
        
        Returns:
            GeoId string veya boş string
        """
        if not location:
            return ""
        
        # Normalize: lowercase, strip
        location_normalized = location.lower().strip()
        
        # Direkt mapping kontrolü
        if location_normalized in SectorBasedScraperSpider.LINKEDIN_GEO_IDS:
            return SectorBasedScraperSpider.LINKEDIN_GEO_IDS[location_normalized]
        
        # Türkçe karakterleri normalize et (ı -> i, ğ -> g, ü -> u, ş -> s, ö -> o, ç -> c)
        turkish_chars = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
        location_normalized_no_turkish = location_normalized
        for turkish, english in turkish_chars.items():
            location_normalized_no_turkish = location_normalized_no_turkish.replace(turkish, english)
        
        if location_normalized_no_turkish in SectorBasedScraperSpider.LINKEDIN_GEO_IDS:
            return SectorBasedScraperSpider.LINKEDIN_GEO_IDS[location_normalized_no_turkish]
        
        # Partial match (örn: "Istanbul, Turkey" -> "istanbul")
        # Önce virgül veya boşluk ile ayrılmış ilk kelimeyi al
        location_first_word = location_normalized.split(',')[0].split()[0] if location_normalized else ""
        if location_first_word and location_first_word in SectorBasedScraperSpider.LINKEDIN_GEO_IDS:
            return SectorBasedScraperSpider.LINKEDIN_GEO_IDS[location_first_word]
        
        # Tüm mapping'de partial match ara
        for city, geo_id in SectorBasedScraperSpider.LINKEDIN_GEO_IDS.items():
            if city in location_normalized or location_normalized in city:
                return geo_id
        
        return ""

    def __init__(self, sector: str = "", location: str = "", geo_id: str = "", limit: str = "20", max_pages: str = "3", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sector = (sector or "").strip()
        self.location = (location or "").strip()
        self.geo_id = (geo_id or "").strip()
        
        # Eğer location verilmişse ama geo_id verilmemişse, otomatik bul
        if self.location and not self.geo_id:
            auto_geo_id = self.get_geo_id_from_location(self.location)
            if auto_geo_id:
                self.geo_id = auto_geo_id
                self.logger.info(f"✅ Auto-detected geo_id '{auto_geo_id}' for location '{self.location}'")
            else:
                self.logger.warning(f"⚠️  Could not find geo_id for location '{self.location}'. Location filtering may not work.")
                self.logger.info(f"   Available locations: {', '.join(list(self.LINKEDIN_GEO_IDS.keys())[:10])}...")
        
        if not self.sector:
            raise ValueError("sector is required. Example: scrapy crawl sector_based_scraper -a sector='Technology'")

        try:
            self.max_pages = max(1, int(max_pages))
        except Exception:
            self.max_pages = 20  # Increased default from 3 to 20 for more comprehensive results
            
        try:
            self.limit = max(1, int(limit))
        except Exception:
            self.limit = 20

        self._seen_company_urls: set[str] = set()
        self.processed_count = 0
        self.enqueued_count = 0  # Track enqueued requests (for pagination decision)
        # Track companies being scraped (website -> company data)
        self.companies_in_progress = {}
        # Track consecutive pages with no new URLs
        self.consecutive_duplicate_pages = 0

    def start_requests(self):
        # Try LinkedIn's sector filtering system first (more accurate results)
        # LinkedIn uses f_I parameter for industry/vertical filtering
        sector_key = self.sector.lower().strip()
        
        # Check if we have LinkedIn sector ID for this sector
        if sector_key in self.LINKEDIN_SECTOR_IDS:
            sector_ids = self.LINKEDIN_SECTOR_IDS[sector_key]
            self.logger.info(f"✅ Found {len(sector_ids)} sector ID(s) for '{sector_key}': {sector_ids}")
            
            # Use ALL sector IDs to get maximum coverage
            # Each ID represents a different subcategory (e.g., BT Hizmetleri, Teknoloji Bilgi ve Medya, etc.)
            for idx, sector_id in enumerate(sector_ids, 1):
                search_url = f"https://www.linkedin.com/search/results/companies/?f_I={sector_id}"
                
                # Location facet için companyHqGeo kullanılmalı. Format: companyHqGeo=["102424322"]
                # LinkedIn URL'de: companyHqGeo=%5B%22102424322%22%5D (URL encoded)
                if self.geo_id:
                    # LinkedIn companyHqGeo formatı: ["102424322"] şeklinde array
                    company_hq_geo_value = f'["{self.geo_id}"]'
                    search_url += f"&companyHqGeo={quote_plus(company_hq_geo_value)}"
                    self.logger.info(f"🔍 [{idx}/{len(sector_ids)}] Starting search with sector ID {sector_id} + companyHqGeo '{self.geo_id}': {search_url}")
                elif self.location:
                    self.logger.warning(
                        f"⚠️  location='{self.location}' verildi ama geo_id yok. LinkedIn location facet companyHqGeo ister; "
                        "location string'i URL'ye eklemiyorum (aksi halde aynı sonuçlar dönebilir)."
                    )
                    self.logger.info(f"🔍 [{idx}/{len(sector_ids)}] Starting search with sector ID {sector_id} (no location filter): {search_url}")
                else:
                    self.logger.info(f"🔍 [{idx}/{len(sector_ids)}] Starting search with sector ID {sector_id} (no location filter): {search_url}")
                
                cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{search_url}"

                # Try direct LinkedIn first (better for JavaScript-rendered content)
                yield scrapy.Request(
                    url=search_url,
                    callback=self.parse_search_results,
                    errback=self.errback_handler,
                    meta={
                        "page": 1,
                        "search_url": search_url,
                        "sector_id": sector_id,
                        "sector_id_index": idx,
                        "total_sector_ids": len(sector_ids),
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
        else:
            # Fallback: Use keywords search (less accurate but works for any sector)
            encoded_sector = quote_plus(self.sector)
            search_url = f"https://www.linkedin.com/search/results/companies/?keywords={encoded_sector}"
            
            # Location facet için companyHqGeo kullanılmalı. Format: companyHqGeo=["102424322"]
            # LinkedIn URL'de: companyHqGeo=%5B%22102424322%22%5D (URL encoded)
            if self.geo_id:
                # LinkedIn companyHqGeo formatı: ["102424322"] şeklinde array
                company_hq_geo_value = f'["{self.geo_id}"]'
                search_url += f"&companyHqGeo={quote_plus(company_hq_geo_value)}"
                self.logger.info(f"⚠️  No LinkedIn sector ID found for '{sector_key}', using keywords search with companyHqGeo '{self.geo_id}': {search_url}")
            elif self.location:
                self.logger.warning(
                    f"⚠️  location='{self.location}' verildi ama geo_id yok. LinkedIn location facet companyHqGeo ister; "
                    "location string'i URL'ye eklemiyorum (aksi halde aynı sonuçlar dönebilir)."
                )
                self.logger.info(f"⚠️  No LinkedIn sector ID found for '{sector_key}', using keywords search (no location filter): {search_url}")
            else:
                self.logger.info(f"⚠️  No LinkedIn sector ID found for '{sector_key}', using keywords search: {search_url}")
            
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
        request = failure.request
        page = request.meta.get("page", 1)
        is_pagination = page > 1
        
        if is_pagination:
            self.logger.error(f"❌ Pagination request failed for page {page}: {failure.value}")
            self.logger.error(f"❌ Failed URL: {request.url}")
        else:
            self.logger.warning(f"⚠️  Initial search request failed: {failure.value}. Trying Google Cache...")
        
        cache_url = request.meta.get("cache_url")
        if cache_url:
            if is_pagination:
                self.logger.info(f"🔄 Retrying pagination page {page} with Google Cache...")
            yield scrapy.Request(
                url=cache_url,
                callback=self.parse_search_results,
                meta={
                    "page": page,
                    "search_url": request.meta.get("search_url"),
                    "sector_id": request.meta.get("sector_id", "N/A"),
                    "sector_id_index": request.meta.get("sector_id_index", ""),
                    "total_sector_ids": request.meta.get("total_sector_ids", ""),
                    "cache_url": cache_url,
                    "use_cache": True
                },
                dont_filter=True
            )
        else:
            self.logger.error(f"❌ No cache URL available for failed request: {request.url}")

    def parse_search_results(self, response):
        page = int(response.meta.get("page", 1))
        search_url = response.meta.get("search_url")
        sector_id = response.meta.get("sector_id", "N/A")
        sector_id_index = response.meta.get("sector_id_index", "")
        total_sector_ids = response.meta.get("total_sector_ids", "")
        
        # Log which sector ID search this is
        if sector_id_index and total_sector_ids:
            self.logger.info(f"📊 Processing page {page} from sector ID {sector_id} ({sector_id_index}/{total_sector_ids}) - Enqueued: {self.enqueued_count}/{self.limit}, Processed: {self.processed_count}/{self.limit}")
        else:
            self.logger.info(f"📊 Processing page {page} - Enqueued: {self.enqueued_count}/{self.limit}, Processed: {self.processed_count}/{self.limit}")

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
        
        self.logger.info(f"📄 Page {page}: Found {len(normalized_urls)} company URLs (raw: {len(company_urls)})")
        
        # If no URLs found, log the response for debugging
        if not normalized_urls:
            self.logger.warning(f"⚠️  No company URLs found on page {page}. Response status: {response.status}")
            self.logger.warning(f"⚠️  Response URL: {response.url}")
            self.logger.debug(f"Response body preview (first 1000 chars): {response.text[:1000]}")
            # Still try pagination if this is the first page (might be a temporary issue)
            if page == 1:
                self.logger.warning(f"⚠️  No URLs on first page, but will try pagination anyway")

        # Count new (non-duplicate) URLs BEFORE adding them to _seen_company_urls
        new_urls_count = 0
        for company_url in normalized_urls:
            base_url = company_url.rstrip('/').replace('/about', '')
            if base_url not in self._seen_company_urls:
                new_urls_count += 1

        self.logger.info(f"Page {page}: {new_urls_count} new URLs, {len(normalized_urls) - new_urls_count} duplicates")

        for company_url in normalized_urls:
            # Check limit before processing more companies (use enqueued_count for async-aware limit check)
            if self.enqueued_count >= self.limit:
                self.logger.info(f"Reached limit of {self.limit} companies (enqueued: {self.enqueued_count})")
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
            self.enqueued_count += 1  # Track enqueued requests for pagination decision
            yield scrapy.Request(
                url=about_url,
                callback=self.parse_company_profile,
                meta={"sector": self.sector, "location": self.location, "company_url": base_url},
                errback=self.handle_company_profile_error,
            )

        # Try pagination: LinkedIn typically supports `start=` parameter for pagination
        # AGGRESSIVE PAGINATION: Continue until we reach the limit or truly run out of results
        
        # Track consecutive duplicate pages
        if new_urls_count == 0:
            self.consecutive_duplicate_pages += 1
        else:
            self.consecutive_duplicate_pages = 0  # Reset counter if we found new URLs
        
        # Calculate effective max pages based on limit (each page has ~10 results)
        # If limit is 50, we need at least 5 pages, but add large buffer for duplicates
        effective_max_pages = max(self.max_pages, (self.limit // 10) + 30)
        
        # Stop if we've had too many consecutive duplicate pages (likely reached end of results)
        # Increased to allow more pages to be checked
        max_consecutive_duplicates = 10  # Increased from 5 to 10
        
        # AGGRESSIVE PAGINATION: Always continue if we haven't reached limit
        # Use enqueued_count instead of processed_count for async-aware pagination decision
        # Only stop if we've hit too many consecutive duplicates OR reached max pages
        should_paginate = (
            self.enqueued_count < self.limit and 
            self.consecutive_duplicate_pages < max_consecutive_duplicates and
            page < effective_max_pages
        )
        
        # Detailed pagination decision logging
        self.logger.info(f"🔍 Pagination check: enqueued={self.enqueued_count}/{self.limit}, processed={self.processed_count}/{self.limit}, consecutive_duplicates={self.consecutive_duplicate_pages}/{max_consecutive_duplicates}, page={page}/{effective_max_pages}")
        self.logger.info(f"🔍 should_paginate={should_paginate}")
        
        if not should_paginate:
            reasons = []
            if self.enqueued_count >= self.limit:
                reasons.append(f"reached_limit(enqueued={self.enqueued_count}>={self.limit})")
            if self.consecutive_duplicate_pages >= max_consecutive_duplicates:
                reasons.append(f"too_many_duplicates({self.consecutive_duplicate_pages}>={max_consecutive_duplicates})")
            if page >= effective_max_pages:
                reasons.append(f"max_pages_reached({page}>={effective_max_pages})")
            self.logger.warning(f"⏹️  Stopping pagination: {', '.join(reasons) if reasons else 'unknown reason'}")
        
        if should_paginate:
            next_page = page + 1
            use_cache = response.meta.get("use_cache", False)
            
            # Get original search_url without pagination parameters (from meta)
            # This ensures we always use the base URL for pagination
            original_search_url = search_url
            # Remove any existing start or page parameter from the URL
            if '&start=' in original_search_url or '?start=' in original_search_url:
                original_search_url = re.sub(r'[&?]start=\d+', '', original_search_url)
            if '&page=' in original_search_url:
                original_search_url = re.sub(r'&page=\d+', '', original_search_url)
            if '?page=' in original_search_url:
                original_search_url = re.sub(r'\?page=\d+', '?', original_search_url)
                # Clean up trailing ? if no other params
                if original_search_url.endswith('?'):
                    original_search_url = original_search_url.rstrip('?')
            
            # Log pagination decision
            self.logger.info(f"📊 Page {page} summary: {len(normalized_urls)} URLs found, {new_urls_count} new, enqueued={self.enqueued_count}/{self.limit}, processed={self.processed_count}/{self.limit}, {self.consecutive_duplicate_pages} consecutive duplicates")
            
            if use_cache:
                # Use Google Cache for pagination
                next_search_url = f"{original_search_url}&page={next_page}"
                next_cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{next_search_url}"
                next_url = next_cache_url
            else:
                # Use direct LinkedIn URL for pagination
                # LinkedIn uses page parameter for pagination: page=1, page=2, page=3, etc.
                # Format: &page=4 (not start=10, start=20)
                
                # Handle both f_I (sector ID) and keywords search formats
                if '?' in original_search_url:
                    next_search_url = f"{original_search_url}&page={next_page}"
                else:
                    next_search_url = f"{original_search_url}?page={next_page}"
                
                next_url = next_search_url
                sector_info = f" (sector ID: {sector_id})" if sector_id != "N/A" else ""
                self.logger.info(f"📄 Requesting page {next_page}{sector_info} (found {new_urls_count} new URLs, enqueued={self.enqueued_count}/{self.limit}, processed={self.processed_count}/{self.limit}, total URLs on page: {len(normalized_urls)})")
                self.logger.info(f"📄 Next URL: {next_url}")
            
            # Create and yield pagination request
            pagination_request = scrapy.Request(
                url=next_url,
                callback=self.parse_search_results,
                errback=self.errback_handler,
                meta={
                    "page": next_page,
                    "search_url": original_search_url,  # Store original URL without start param
                    "sector_id": sector_id,
                    "sector_id_index": sector_id_index,
                    "total_sector_ids": total_sector_ids,
                    "cache_url": f"https://webcache.googleusercontent.com/search?q=cache:{original_search_url}&page={next_page}",
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
            self.logger.info(f"✅ Yielding pagination request for page {next_page}: {next_url}")
            yield pagination_request
        else:
            # Log why we're stopping
            if self.processed_count >= self.limit:
                self.logger.info(f"✅ Stopping pagination: Reached limit of {self.limit} companies")
            elif self.consecutive_duplicate_pages >= max_consecutive_duplicates:
                self.logger.info(f"⏹️  Stopping pagination: {self.consecutive_duplicate_pages} consecutive pages with no new URLs (likely reached end of results)")
            elif page >= effective_max_pages:
                self.logger.info(f"⏹️  Stopping pagination: Reached max pages limit ({effective_max_pages})")
            else:
                self.logger.info(f"⏹️  Stopping pagination: Unknown reason")

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
            '.org-top-card-summary-info-list__item:contains("Telefon")::text',  # Türkçe
            '.org-top-card-summary-info-list__item:contains("telefon")::text',
            'dt:contains("Phone") + dd::text',
            'dt:contains("Telefon") + dd::text',
            'dd:contains("+")::text',  # + işareti içeren dd elementleri
            'dd:contains("0")::text',  # 0 ile başlayan telefonlar (Türk formatı)
            '.core-section-container__content:contains("Phone")::text',
            '.core-section-container__content:contains("Telefon")::text',
        ]
        for selector in phone_selectors:
            try:
                phone_text = response.css(selector).get()
                if phone_text:
                    # Remove tel: prefix if present
                    phone_text = phone_text.replace('tel:', '').strip()
                    # Extract phone from tel: link or text
                    phone_match = self.PHONE_PATTERN.search(phone_text)
                    if phone_match:
                        phone_candidate = phone_match.group(0).strip()
                        
                        # Clean up phone number (remove extra spaces, normalize)
                        phone_candidate = re.sub(r'\s+', ' ', phone_candidate)
                        
                        # Count digits only (not characters)
                        digits_only = re.sub(r'[^\d]', '', phone_candidate)
                        
                        # Skip if too short or too long
                        if len(digits_only) < 10 or len(digits_only) > 15:
                            continue
                        
                        # Filter out false positives:
                        # - Version numbers like "10.001", "20.55", "1.19963", "6.0039"
                        #   Pattern: X.Y, X.YY, X.YYY, X.YYYY, X.YYYYY (where X is 1-2 digits, Y is 1-5 digits)
                        if re.match(r'^\d{1,2}\.\d{1,5}$', phone_candidate):
                            self.logger.debug(f"Skipping version number: {phone_candidate}")
                            continue
                        # - Version numbers with spaces like "20.55 13 21 12" (version + other text)
                        #   Check if it starts with a version number pattern
                        phone_parts = phone_candidate.split()
                        if len(phone_parts) > 1 and re.match(r'^\d{1,2}\.\d{1,5}$', phone_parts[0]):
                            self.logger.debug(f"Skipping version number with text: {phone_candidate}")
                            continue
                        # - IP addresses
                        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', phone_candidate):
                            self.logger.debug(f"Skipping IP address: {phone_candidate}")
                            continue
                        # - Just 4 digits (years)
                        if re.match(r'^\d{4}$', phone_candidate):
                            self.logger.debug(f"Skipping year: {phone_candidate}")
                            continue
                        # - Employee count ranges like "201-500", "1-10", "11-50", "51-200"
                        if re.match(r'^\d{1,4}-\d{1,4}$', phone_candidate):
                            self.logger.debug(f"Skipping employee count range: {phone_candidate}")
                            continue
                        # - Email-like patterns (contains @ or looks like email)
                        if '@' in phone_candidate or re.search(r'[a-zA-Z]', phone_candidate):
                            self.logger.debug(f"Skipping email-like pattern: {phone_candidate}")
                            continue
                        # - Check if phone has multiple parts separated by spaces (might be version + text)
                        #   If it has more than 3 parts, it's likely not a phone number
                        if len(phone_parts) > 3:
                            self.logger.debug(f"Skipping multi-part text (likely not phone): {phone_candidate}")
                            continue
                        
                        # If we get here, it's a valid phone number
                        phone_from_linkedin = phone_candidate
                        self.logger.info(f"✅ Found phone on LinkedIn: {phone_from_linkedin}")
                        break
            except Exception as e:
                self.logger.debug(f"Error with phone selector {selector}: {e}")
                continue
        
        # If not found in selectors, try searching in visible text
        if not phone_from_linkedin:
            try:
                # Get visible text from the page
                visible_text_elements = response.css("body *:not(script):not(style)::text").getall()
                visible_text = " ".join([t.strip() for t in visible_text_elements if t.strip() and len(t.strip()) < 500])
                
                # Search for phone patterns in visible text
                phone_matches = self.PHONE_PATTERN.findall(visible_text)
                if phone_matches:
                    # Filter out false positives (too short, looks like dates, etc.)
                    for phone_candidate in phone_matches:
                        phone_clean = phone_candidate.strip()
                        # Count digits only (not characters)
                        digits_only = re.sub(r'[^\d]', '', phone_clean)
                        
                        # Skip if too short or too long
                        if len(digits_only) >= 10 and len(digits_only) <= 15:
                            # Filter out false positives:
                            # - Version numbers like "10.001", "20.55", "1.19963", "6.0039"
                            #   Pattern: X.Y, X.YY, X.YYY, X.YYYY, X.YYYYY (where X is 1-2 digits, Y is 1-5 digits)
                            if re.match(r'^\d{1,2}\.\d{1,5}$', phone_clean):
                                self.logger.debug(f"Skipping version number: {phone_clean}")
                                continue
                            # - Version numbers with spaces like "20.55 13 21 12" (version + other text)
                            #   Check if it starts with a version number pattern
                            phone_parts = phone_clean.split()
                            if len(phone_parts) > 1 and re.match(r'^\d{1,2}\.\d{1,5}$', phone_parts[0]):
                                self.logger.debug(f"Skipping version number with text: {phone_clean}")
                                continue
                            # - IP addresses
                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', phone_clean):
                                self.logger.debug(f"Skipping IP address: {phone_clean}")
                                continue
                            # - Just 4 digits (years)
                            if re.match(r'^\d{4}$', phone_clean):
                                self.logger.debug(f"Skipping year: {phone_clean}")
                                continue
                            # - Employee count ranges like "201-500", "1-10", "11-50"
                            if re.match(r'^\d{1,4}-\d{1,4}$', phone_clean):
                                self.logger.debug(f"Skipping employee count range: {phone_clean}")
                                continue
                            # - Email-like patterns (contains @ or looks like email)
                            if '@' in phone_clean or re.search(r'[a-zA-Z]', phone_clean):
                                self.logger.debug(f"Skipping email-like pattern: {phone_clean}")
                                continue
                            # - Check if phone has multiple parts separated by spaces (might be version + text)
                            #   If it has more than 3 parts, it's likely not a phone number
                            if len(phone_parts) > 3:
                                self.logger.debug(f"Skipping multi-part text (likely not phone): {phone_clean}")
                                continue
                            # - Should look like a phone number (has +, 0, or proper format)
                            if (phone_clean.startswith('+') or 
                                phone_clean.startswith('0') or 
                                re.match(r'^\+?\d{1,3}', phone_clean) or
                                '(' in phone_clean or '-' in phone_clean):
                                phone_from_linkedin = phone_clean
                                self.logger.info(f"✅ Found phone in page text: {phone_from_linkedin}")
                                break
            except Exception as e:
                self.logger.debug(f"Error searching for phone in visible text: {e}")
        
        email_selectors = [
            'a[href^="mailto:"]::attr(href)',
            'a[href^="mailto:"]::text',
            'dd a[href^="mailto:"]::attr(href)',  # About page structure
            'dd a[href^="mailto:"] span::text',
            '.org-top-card-summary-info-list__item:contains("@")::text',
        ]
        for selector in email_selectors:
            try:
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
                        # Filter out false positives
                        email_lower = email_from_linkedin.lower()
                        if not any(skip in email_lower for skip in ['example.com', 'test@', 'noreply@', 'no-reply@', 'placeholder@', '@example']):
                            self.logger.info(f"✅ Found email on LinkedIn: {email_from_linkedin}")
                            break
            except Exception as e:
                self.logger.debug(f"Error with email selector {selector}: {e}")
                continue
        
        # If not found in selectors, try searching in visible text
        if not email_from_linkedin:
            try:
                # Get visible text from the page
                visible_text_elements = response.css("body *:not(script):not(style)::text").getall()
                visible_text = " ".join([t.strip() for t in visible_text_elements if t.strip() and len(t.strip()) < 500])
                
                # Search for email patterns in visible text
                email_matches = self.EMAIL_PATTERN.findall(visible_text)
                if email_matches:
                    # Filter out common false positives
                    for email_candidate in email_matches:
                        email_lower = email_candidate.lower()
                        # Skip common false positives
                        if not any(skip in email_lower for skip in ['example.com', 'test@', 'noreply@', 'no-reply@', 'placeholder@', '@example', 'email@', 'mail@']):
                            # Check if it's a valid email format
                            if '.' in email_candidate.split('@')[1] if '@' in email_candidate else False:
                                email_from_linkedin = email_candidate
                                self.logger.info(f"✅ Found email in page text: {email_from_linkedin}")
                                break
            except Exception as e:
                self.logger.debug(f"Error searching for email in visible text: {e}")

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
            
            # Check if phone from LinkedIn is valid (not an employee count range)
            phone_is_valid = True
            if phone_from_linkedin:
                # Check if it looks like an employee count range (e.g., "201-500", "1-10")
                if re.match(r'^\d{1,4}-\d{1,4}$', phone_from_linkedin):
                    phone_is_valid = False
                    self.logger.info(f"⚠️  Invalid phone from LinkedIn (looks like employee count): {phone_from_linkedin}, will search website")
            
            # Initialize tracking for this company
            company_key = website
            self.companies_in_progress[company_key] = {
                'company_name': company_name,
                'phone': phone_from_linkedin if phone_is_valid else "",
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
        filtered_emails = set()
        for email in emails_found:
            # Basic checks
            if email.startswith('//') or '@' not in email:
                continue
            if email.endswith(('.png', '.jpg', '.gif', '.css', '.js')):
                continue
            # False positive checks
            email_lower = email.lower()
            if any(skip in email_lower for skip in ['example.com', 'test@', 'noreply@', 'no-reply@', 'placeholder@', '@example', 'email@', 'mail@']):
                continue
            # Email format validation
            if '@' in email:
                parts = email.split('@')
                if len(parts) == 2:
                    local_part, domain = parts
                    # Local part boş olmamalı
                    if len(local_part) == 0:
                        continue
                    # Domain'de nokta olmalı
                    if '.' not in domain:
                        continue
                    # Domain name boş olmamalı
                    domain_parts = domain.split('.')
                    if len(domain_parts[0]) == 0:
                        continue
                    filtered_emails.add(email)
        emails_found = filtered_emails
        
        if emails_found:
            self.logger.info(f"Found {len(emails_found)} emails on {response.url}")
            company_data['emails'].update(emails_found)
        
        # Extract phone numbers from page text
        phones_found = self.PHONE_PATTERN.findall(page_text)
        if phones_found:
            # Only update if we don't have a valid phone yet
            current_phone = company_data.get('phone', '')
            # Check if current phone is invalid (employee count range or empty)
            should_update_phone = not current_phone or re.match(r'^\d{1,4}-\d{1,4}$', current_phone)
            
            if should_update_phone:
                # Use the first valid phone number found
                for phone in phones_found:
                    # Clean up phone number
                    phone_clean = re.sub(r'[^\d+\-().\s]', '', phone).strip()
                    # Remove extra spaces
                    phone_clean = re.sub(r'\s+', ' ', phone_clean)
                    
                    # Filter out false positives:
                    # - Too short (less than 10 digits)
                    # - Looks like a date/year (4 digits)
                    # - Too many digits (likely not a phone)
                    digits_only = re.sub(r'[^\d]', '', phone_clean)
                    if len(digits_only) >= 10 and len(digits_only) <= 15:
                        # Filter out false positives:
                        # - Version numbers like "10.001", "20.55", "1.19963", "6.0039"
                        #   Pattern: X.Y, X.YY, X.YYY, X.YYYY, X.YYYYY (where X is 1-2 digits, Y is 1-5 digits)
                        if re.match(r'^\d{1,2}\.\d{1,5}$', phone_clean):
                            self.logger.debug(f"Skipping version number: {phone_clean}")
                            continue
                        # - Version numbers with spaces like "20.55 13 21 12" (version + other text)
                        #   Check if it starts with a version number pattern
                        phone_parts = phone_clean.split()
                        if len(phone_parts) > 1 and re.match(r'^\d{1,2}\.\d{1,5}$', phone_parts[0]):
                            self.logger.debug(f"Skipping version number with text: {phone_clean}")
                            continue
                        # - IP addresses
                        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', phone_clean):
                            self.logger.debug(f"Skipping IP address: {phone_clean}")
                            continue
                        # - Just 4 digits (years)
                        if re.match(r'^\d{4}$', phone_clean):
                            self.logger.debug(f"Skipping year: {phone_clean}")
                            continue
                        # - Employee count ranges like "201-500", "1-10"
                        if re.match(r'^\d{1,4}-\d{1,4}$', phone_clean):
                            self.logger.debug(f"Skipping employee count range: {phone_clean}")
                            continue
                        # - Email-like patterns (contains @ or looks like email)
                        if '@' in phone_clean or re.search(r'[a-zA-Z]', phone_clean):
                            self.logger.debug(f"Skipping email-like pattern: {phone_clean}")
                            continue
                        # - Check if phone has multiple parts separated by spaces (might be version + text)
                        #   If it has more than 3 parts, it's likely not a phone number
                        if len(phone_parts) > 3:
                            self.logger.debug(f"Skipping multi-part text (likely not phone): {phone_clean}")
                            continue
                        # Additional validation: should contain country code or area code pattern
                        # Turkish: starts with 0 or +90, or has area code pattern
                        # International: starts with + or has country code
                        if (phone_clean.startswith('+') or 
                            phone_clean.startswith('0') or 
                            re.match(r'^\+?\d{1,3}', phone_clean) or
                            '(' in phone_clean or '-' in phone_clean):
                            company_data['phone'] = phone_clean
                            self.logger.info(f"✅ Found phone number on {response.url}: {phone_clean}")
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
        
        # Check error type - skip logging for common non-critical errors
        error_value = str(failure.value) if failure.value else ""
        status_code = None
        if hasattr(failure.value, 'response') and failure.value.response:
            status_code = failure.value.response.status
        
        # Only log warnings for non-404/403 errors (404/403 are expected for many sites)
        if status_code not in [404, 403]:
            self.logger.warning(f"Failed to scrape {failure.request.url}: {error_value[:100]}")
        else:
            # Silently skip 404/403 errors (common for contact pages)
            self.logger.debug(f"Skipping {failure.request.url}: {status_code}")
        
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

