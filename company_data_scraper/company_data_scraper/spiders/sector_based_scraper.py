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
        if page < self.max_pages and normalized_urls:  # Only paginate if we found results
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
        company_item = {}
        company_item["sector_query"] = response.meta.get("sector", self.sector)
        company_item["company_linkedin_url"] = response.meta.get("company_url", response.url)

        company_item["company_name"] = (
            response.css(".top-card-layout__entity-info h1::text").get(default="not-found").strip()
        )

        followers_text = response.xpath(
            '//h3[contains(@class, "top-card-layout__first-subline")]/span/following-sibling::text()'
        ).get()
        if followers_text:
            try:
                company_item["linkedin_followers_count"] = int(
                    followers_text.split()[0].strip().replace(",", "")
                )
            except Exception:
                company_item["linkedin_followers_count"] = followers_text.strip()
        else:
            company_item["linkedin_followers_count"] = "not-found"

        company_item["company_logo_url"] = response.css(
            "div.top-card-layout__entity-image-container img::attr(data-delayed-url)"
        ).get("not-found")

        company_item["about_us"] = response.css(".core-section-container__content p::text").get(
            default="not-found"
        ).strip()

        # num_of_employees
        try:
            raw = response.css("a.face-pile__cta::text").get(default="not-found").strip()
            match = re.findall(r"\d{1,3}(?:,\d{3})*", raw)
            if match:
                company_item["num_of_employees"] = int(match[0].replace(",", ""))
            else:
                company_item["num_of_employees"] = raw
        except Exception:
            company_item["num_of_employees"] = "not-found"

        # Company details block (same approach as existing company_profile_scraper spider)
        try:
            company_details = response.css(".core-section-container__content .mb-2")

            company_item["website"] = company_details[0].css("a::text").get(default="not-found").strip()

            industry_line = company_details[1].css(".text-md::text").getall()
            company_item["industry"] = industry_line[1].strip() if len(industry_line) > 1 else "not-found"

            size_line = company_details[2].css(".text-md::text").getall()
            company_item["company_size_approx"] = (
                size_line[1].strip().split()[0] if len(size_line) > 1 else "not-found"
            )

            hq_line = company_details[3].css(".text-md::text").getall()
            if hq_line and hq_line[0].lower().strip() == "headquarters":
                company_item["headquarters"] = hq_line[1].strip() if len(hq_line) > 1 else "not-found"
            else:
                company_item["headquarters"] = "not-found"

            type_line = company_details[4].css(".text-md::text").getall()
            company_item["type"] = type_line[1].strip() if len(type_line) > 1 else "not-found"

            unsure_param = company_details[5].css(".text-md::text").getall()
            unsure_key = unsure_param[0].lower().strip() if unsure_param else "unsure_parameter"
            unsure_val = unsure_param[1].strip() if len(unsure_param) > 1 else "not-found"
            company_item[unsure_key] = unsure_val

            # founded/specialties normalization
            if unsure_key == "founded":
                specialties_line = company_details[6].css(".text-md::text").getall() if len(company_details) > 6 else []
                if specialties_line and specialties_line[0].lower().strip() == "specialties":
                    company_item["specialties"] = specialties_line[1].strip() if len(specialties_line) > 1 else "not-found"
                else:
                    company_item["specialties"] = "not-found"
            else:
                company_item.setdefault("founded", "not-found")
                company_item.setdefault("specialties", "not-found")

            # Funding fields (best-effort)
            company_item["funding"] = response.css("p.text-display-lg::text").get(default="not-found").strip()

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

        except Exception:
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

