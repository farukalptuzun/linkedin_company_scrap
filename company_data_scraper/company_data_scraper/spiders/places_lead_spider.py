"""
Google Places API based lead scraper
Scrapes companies by sector and location, extracts phone numbers and emails
"""
import scrapy
import json
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime
from scrapy.http import Request
from company_data_scraper.items import LeadItem


class PlacesLeadSpider(scrapy.Spider):
    name = 'places_lead_spider'
    
    # Email regex pattern (matches most common email formats)
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
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
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Create spider instance with access to crawler settings"""
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        # Get API key from settings
        spider.api_key = crawler.settings.get('GOOGLE_PLACES_API_KEY')
        if not spider.api_key:
            spider.logger.error("GOOGLE_PLACES_API_KEY not found in settings or environment variables!")
            raise ValueError("GOOGLE_PLACES_API_KEY is required")
        return spider
    
    def __init__(self, sector=None, location=None, limit=20, *args, **kwargs):
        super(PlacesLeadSpider, self).__init__(*args, **kwargs)
        self.sector = sector
        self.location = location
        self.limit = int(limit) if limit else 20
        self.processed_count = 0
        self.api_key = None  # Will be set in from_crawler
        # Track companies being scraped (website -> company data)
        self.companies_in_progress = {}
        
        if not self.sector or not self.location:
            self.logger.error("Both --sector and --location arguments are required!")
            raise ValueError("sector and location are required")
    
    def start_requests(self):
        """Start with Google Places Text Search API"""
        query = f"{self.sector} in {self.location}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': query,
            'key': self.api_key,
        }
        
        self.logger.info(f"Starting search: {query}")
        self.logger.info(f"Limit: {self.limit} companies")
        
        yield Request(
            url=f"{url}?query={params['query']}&key={params['key']}",
            callback=self.parse_places_search,
            meta={'next_page_token': None}
        )
    
    def parse_places_search(self, response):
        """Parse Google Places Text Search results"""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON response: {response.text[:200]}")
            return
        
        if data.get('status') != 'OK' and data.get('status') != 'ZERO_RESULTS':
            self.logger.error(f"Google Places API error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
            return
        
        if data.get('status') == 'ZERO_RESULTS':
            self.logger.info("No results found for the search query")
            return
        
        results = data.get('results', [])
        self.logger.info(f"Found {len(results)} results in this page")
        
        # Process each place
        for place in results:
            if self.processed_count >= self.limit:
                self.logger.info(f"Reached limit of {self.limit} companies")
                return
            
            place_id = place.get('place_id')
            if not place_id:
                continue
            
            # Request Place Details
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place_id,
                'fields': 'name,formatted_phone_number,website,international_phone_number',
                'key': self.api_key,
            }
            
            yield Request(
                url=f"{details_url}?place_id={details_params['place_id']}&fields={details_params['fields']}&key={details_params['key']}",
                callback=self.parse_place_details,
                meta={'place': place}
            )
        
        # Check for next page
        next_page_token = data.get('next_page_token')
        if next_page_token and self.processed_count < self.limit:
            self.logger.info("Waiting 2 seconds before requesting next page (Google API requirement)...")
            time.sleep(2)
            
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            yield Request(
                url=f"{url}?pagetoken={next_page_token}&key={self.api_key}",
                callback=self.parse_places_search,
                meta={'next_page_token': next_page_token}
            )
    
    def parse_place_details(self, response):
        """Parse Place Details and extract company information"""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse Place Details JSON: {response.text[:200]}")
            return
        
        if data.get('status') != 'OK':
            self.logger.error(f"Place Details API error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
            return
        
        result = data.get('result', {})
        place = response.meta.get('place', {})
        
        company_name = result.get('name') or place.get('name', '')
        phone = result.get('formatted_phone_number') or result.get('international_phone_number', '')
        website = result.get('website', '')
        
        if not company_name:
            self.logger.warning("Skipping place without name")
            return
        
        self.processed_count += 1
        self.logger.info(f"[{self.processed_count}/{self.limit}] Processing: {company_name}")
        
        # If website exists, scrape it for emails
        if website:
            # Normalize website URL
            if not website.startswith('http'):
                website = 'https://' + website
            
            # Initialize tracking for this company
            company_key = website
            self.companies_in_progress[company_key] = {
                'company_name': company_name,
                'phone': phone,
                'website': website,
                'emails': set(),
                'pages_processed': 0,
                'total_pages': len(self.CONTACT_PATHS),
            }
            
            # Request multiple pages from the website
            for path in self.CONTACT_PATHS:
                url = urljoin(website, path)
                yield Request(
                    url=url,
                    callback=self.parse_website_for_emails,
                    meta={
                        'company_key': company_key,
                        'dont_redirect': True,
                    },
                    errback=self.handle_website_error,
                    dont_filter=False,
                )
        else:
            # No website, yield item with empty emails
            item = LeadItem(
                sector=self.sector,
                location=self.location,
                company_name=company_name,
                phone=phone,
                emails=[],
                website=website,
                source='google_places',
                created_at=datetime.utcnow(),
            )
            yield item
    
    def parse_website_for_emails(self, response):
        """Extract emails from website pages"""
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
        
        # Filter out common non-email patterns (like image URLs)
        emails_found = {
            email for email in emails_found
            if not email.startswith('//') and '@' in email
        }
        
        if emails_found:
            self.logger.info(f"Found {len(emails_found)} emails on {response.url}")
            company_data['emails'].update(emails_found)
        
        # Check if all pages have been processed
        if company_data['pages_processed'] >= company_data['total_pages']:
            # All pages processed, yield final item
            item = LeadItem(
                sector=self.sector,
                location=self.location,
                company_name=company_data['company_name'],
                phone=company_data['phone'],
                emails=list(company_data['emails']),
                website=company_data['website'],
                source='google_places',
                created_at=datetime.utcnow(),
            )
            self.logger.info(
                f"Completed scraping {company_data['company_name']}: "
                f"{len(company_data['emails'])} emails found"
            )
            # Remove from tracking
            del self.companies_in_progress[company_key]
            yield item
    
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
                sector=self.sector,
                location=self.location,
                company_name=company_data['company_name'],
                phone=company_data['phone'],
                emails=list(company_data['emails']),
                website=company_data['website'],
                source='google_places',
                created_at=datetime.utcnow(),
            )
            self.logger.info(
                f"Completed scraping {company_data['company_name']} "
                f"(with some errors): {len(company_data['emails'])} emails found"
            )
            # Remove from tracking
            del self.companies_in_progress[company_key]
            yield item
