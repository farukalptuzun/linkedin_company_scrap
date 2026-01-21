BOT_NAME = "company_data_scraper"

SPIDER_MODULES = ["company_data_scraper.spiders"]
NEWSPIDER_MODULE = "company_data_scraper.spiders"

USER_AGENT = "Mozilla/5.0 (Linux; Android 11; Redmi Note 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"

ROBOTSTXT_OBEY = False

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Be polite / reduce ban risk
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4

# HTTP 999 (LinkedIn rate limit) için retry
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 999]
RETRY_TIMES = 3
RETRY_PRIORITY_ADJUST = -1

# Single pipeline entry point
ITEM_PIPELINES = {
    "company_data_scraper.pipelines.CompanyDataScraperPipeline": 300,
}

# Selenium middleware for JavaScript-rendered pages
DOWNLOADER_MIDDLEWARES = {
    "company_data_scraper.middlewares.SeleniumMiddleware": 543,
}