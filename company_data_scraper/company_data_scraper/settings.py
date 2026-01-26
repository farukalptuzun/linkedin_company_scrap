BOT_NAME = "company_data_scraper"

SPIDER_MODULES = ["company_data_scraper.spiders"]
NEWSPIDER_MODULE = "company_data_scraper.spiders"

USER_AGENT = "Mozilla/5.0 (Linux; Android 11; Redmi Note 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"

ROBOTSTXT_OBEY = False

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Be polite / reduce ban risk
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4

# Retry settings
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_TIMES = 3
RETRY_PRIORITY_ADJUST = -1

# Timeout settings - reduced for faster website scraping
DOWNLOAD_TIMEOUT = 30  # Reduced from default 180s to 30s

# MongoDB settings (can be overridden by environment variables)
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.getenv('MONGO_DB', 'leads_db')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'company_leads')

# Google Places API settings
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', '')

# Pipeline configuration - MongoDB pipeline active
ITEM_PIPELINES = {
    "company_data_scraper.pipelines.MongoPipeline": 300,
}

# Selenium middleware enabled for LinkedIn scraping
# (Required for LinkedIn scraping with cookie support)
DOWNLOADER_MIDDLEWARES = {
    "company_data_scraper.middlewares.SeleniumMiddleware": 543,
}