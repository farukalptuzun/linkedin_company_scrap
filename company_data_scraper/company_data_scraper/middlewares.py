# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class CompanyDataScraperSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class CompanyDataScraperDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class SeleniumMiddleware:
    """Selenium middleware for JavaScript-rendered LinkedIn pages"""
    
    def __init__(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            from company_data_scraper.cookie_manager import LinkedInCookieManager
            import os
            import time
            
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')  # Yeni headless mod
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Try to find Chrome binary on macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
            ]
            
            chrome_binary = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    chrome_options.binary_location = chrome_binary
                    break
            
            # Cookie yöneticisini başlat
            self.cookie_manager = LinkedInCookieManager()
            
            # Cookie'leri kontrol et ve gerekirse yenile
            cookies_loaded = self.cookie_manager.check_and_refresh_cookies(auto_refresh=True)
            
            # Try to use webdriver-manager for automatic driver management
            try:
                service = Service(ChromeDriverManager().install())
                if chrome_binary:
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e1:
                # Fallback: try without webdriver-manager
                try:
                    if chrome_binary:
                        self.driver = webdriver.Chrome(options=chrome_options)
                    else:
                        self.driver = webdriver.Chrome(options=chrome_options)
                except Exception as e2:
                    raise Exception(f"Chrome initialization failed. Chrome binary: {chrome_binary}, Error1: {e1}, Error2: {e2}")
            
            # Cookie'leri yükle
            if cookies_loaded:
                cookies = self.cookie_manager.get_cookies()
                # Önce bir sayfaya git (cookie eklemek için)
                self.driver.get("https://www.linkedin.com")
                time.sleep(1)
                # Cookie'leri ekle
                cookies_added = 0
                for cookie in cookies:
                    try:
                        # Selenium cookie formatına çevir
                        if 'expiry' in cookie:
                            # expiry değeri çok büyükse (expired) atla veya düzelt
                            if cookie['expiry'] > 2147483647:  # Max int32
                                cookie['expiry'] = int(time.time()) + 86400  # 1 gün ekle
                        self.driver.add_cookie(cookie)
                        cookies_added += 1
                    except Exception as e:
                        pass  # Bazı cookie'ler eklenemeyebilir
                print(f"✅ {cookies_added}/{len(cookies)} cookie yüklendi")
            else:
                print("⚠️  Cookie bulunamadı. İlk kurulum için: python3 setup_linkedin_login.py")
            
            self.driver.implicitly_wait(10)
            self.driver_initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize Selenium: {e}")
            print("\nTo fix this:")
            print("1. Install Google Chrome: https://www.google.com/chrome/")
            print("2. Or install Chromium: brew install --cask chromium")
            print("3. ChromeDriver will be downloaded automatically by webdriver-manager")
            self.driver_initialized = False
            self.driver = None
        
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
        
    def process_request(self, request, spider):
        # Use Selenium for both LinkedIn search pages AND company profile pages
        if not self.driver_initialized:
            return None
        
        # Check if this is a LinkedIn page that needs JavaScript rendering
        is_search_page = 'linkedin.com/search/results/companies' in request.url and 'webcache' not in request.url
        is_company_profile = 'linkedin.com/company/' in request.url and 'webcache' not in request.url
        
        if is_search_page or is_company_profile:
            try:
                import time
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                
                self.driver.get(request.url)
                # Wait for page to load - check for main content
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except:
                    pass
                time.sleep(5)  # Extra wait for JavaScript to render content
                
                # Login sayfasına yönlendirilmiş mi kontrol et
                if 'login' in self.driver.current_url.lower() or 'authwall' in self.driver.current_url.lower():
                    spider.logger.error("❌ LinkedIn login sayfasına yönlendirildi. Cookie'ler expire olmuş olabilir.")
                    
                    # Otomatik yenileme dene
                    spider.logger.info("🔄 Otomatik cookie yenileme deneniyor...")
                    if self.cookie_manager.auto_refresh_cookies():
                        # Yenilenen cookie'leri yükle
                        cookies = self.cookie_manager.get_cookies()
                        self.driver.get("https://www.linkedin.com")
                        time.sleep(1)
                        for cookie in cookies:
                            try:
                                if 'expiry' in cookie and cookie['expiry'] > 2147483647:
                                    cookie['expiry'] = int(time.time()) + 86400
                                self.driver.add_cookie(cookie)
                            except:
                                pass
                        
                        # Tekrar dene
                        self.driver.get(request.url)
                        time.sleep(3)
                        
                        if 'login' in self.driver.current_url.lower() or 'authwall' in self.driver.current_url.lower():
                            spider.logger.error("💡 Otomatik yenileme başarısız. Manuel yenileme gerekli: python3 setup_linkedin_login.py")
                            return None
                        else:
                            spider.logger.info("✅ Cookie'ler yenilendi ve sayfa yüklendi!")
                    else:
                        spider.logger.error("💡 Çözüm: python3 setup_linkedin_login.py çalıştırın")
                        return None
                # Sayfa kaynağını al
                body = self.driver.page_source.encode('utf-8')
                
                # Create a new response with the rendered HTML
                from scrapy.http import HtmlResponse
                return HtmlResponse(
                    url=request.url,
                    body=body,
                    encoding='utf-8',
                    request=request
                )
            except Exception as e:
                spider.logger.error(f"Selenium error for {request.url}: {e}")
                return None
        return None
    
    def spider_closed(self, spider):
        if self.driver_initialized and self.driver:
            try:
                self.driver.quit()
            except:
                pass
