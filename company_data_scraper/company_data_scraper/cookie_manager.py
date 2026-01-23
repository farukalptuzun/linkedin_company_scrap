import json
import os
import pickle
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class LinkedInCookieManager:
    """LinkedIn cookie'lerini yönetir ve saklar"""
    
    def __init__(self, cookie_file_path: str = None):
        # Cookie dosyasını proje root'una kaydet
        if cookie_file_path:
            self.cookie_file = cookie_file_path
        else:
            # Proje root'unu bul (company_data_scraper'ın 2 üst dizini)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            self.cookie_file = os.path.join(project_root, ".linkedin_cookies.pkl")
        
        self.cookies = None
        
    def load_cookies(self):
        """Kaydedilmiş cookie'leri yükle"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'rb') as f:
                    self.cookies = pickle.load(f)
                return True
            except Exception as e:
                print(f"Cookie yüklenirken hata: {e}")
                return False
        return False
    
    def save_cookies(self, cookies):
        """Cookie'leri kaydet"""
        try:
            # Dizin yoksa oluştur
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            self.cookies = cookies
            print(f"✅ Cookie'ler kaydedildi: {self.cookie_file}")
            return True
        except Exception as e:
            print(f"Cookie kaydedilirken hata: {e}")
            return False
    
    def get_cookies(self):
        """Cookie'leri döndür"""
        return self.cookies
    
    def are_cookies_expired(self):
        """Cookie'lerin expire olup olmadığını kontrol et"""
        if not self.cookies:
            return True
        
        current_time = int(time.time())
        # En önemli cookie'lerden birini kontrol et (li_at genelde en uzun süreli)
        for cookie in self.cookies:
            if cookie.get('name') == 'li_at':
                expiry = cookie.get('expiry', 0)
                # Expire olmadan 1 gün kala uyarı ver
                if expiry > 0 and expiry < current_time + 86400:
                    return True
                break
        
        return False
    
    def check_and_refresh_cookies(self, auto_refresh: bool = False):
        """
        Cookie'leri kontrol et ve gerekirse yenile
        auto_refresh=True: Expire olmuşsa otomatik yenilemeyi dene
        """
        if not self.load_cookies():
            return False
        
        if self.are_cookies_expired():
            if auto_refresh:
                print("🔄 Cookie'ler expire olmuş, otomatik yenileme deneniyor...")
                return self.auto_refresh_cookies()
            else:
                print("⚠️  Cookie'ler expire olmuş veya expire olmak üzere!")
                return False
        
        return True
    
    def auto_refresh_cookies(self):
        """
        Cookie'leri otomatik yenile (headless modda)
        Not: LinkedIn'in bot detection'ı nedeniyle tam otomasyon zor olabilir
        """
        print("🔄 Otomatik cookie yenileme başlatılıyor...")
        try:
            # Headless modda yenileme dene
            result = self.setup_login(headless=True)
            if result:
                print("✅ Cookie'ler otomatik olarak yenilendi!")
                return True
            else:
                print("⚠️  Otomatik yenileme başarısız. Manuel yenileme gerekebilir.")
                return False
        except Exception as e:
            print(f"❌ Otomatik yenileme hatası: {e}")
            return False
    
    def setup_login(self, headless: bool = False):
        """
        İlk kurulum: LinkedIn'e login yap ve cookie'leri kaydet
        headless=False: Chrome görünür modda açılır, manuel login yaparsın
        """
        print("\n🔐 LinkedIn Login Kurulumu")
        print("=" * 50)
        if headless:
            print("Headless modda otomatik yenileme deneniyor...")
        else:
            print("Chrome açılacak, LinkedIn'e login yapın.")
            print("Login tamamlandıktan sonra bu pencereyi kapatabilirsiniz.")
        print("=" * 50)
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Chrome binary bul
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                chrome_options.binary_location = chrome_binary
                break
        
        try:
            service = Service(ChromeDriverManager().install())
            if chrome_binary:
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"❌ Chrome başlatılamadı: {e}")
            return False
        
        try:
            # LinkedIn login sayfasına git
            driver.get("https://www.linkedin.com/login")
            
            if not headless:
                print("\n⏳ LinkedIn'de login yapın...")
                print("Login tamamlandıktan sonra buraya dönüp Enter'a basın.")
                input("Login tamamlandı mı? (Enter'a basın): ")
            else:
                # Headless modda biraz bekle (login için zaman tanı)
                print("⏳ Headless modda 60 saniye bekleniyor...")
                print("⚠️  Not: Headless modda otomatik login zor olabilir.")
                print("    Manuel login için headless=False kullanın.")
                time.sleep(60)
            
            # Ana sayfaya git (login başarılıysa)
            driver.get("https://www.linkedin.com/feed")
            time.sleep(3)
            
            # Cookie'leri al
            cookies = driver.get_cookies()
            
            if cookies:
                # Login kontrolü: "feed" sayfasında olmalıyız
                if "linkedin.com/feed" in driver.current_url or len(cookies) > 5:
                    self.save_cookies(cookies)
                    print("✅ Login başarılı! Cookie'ler kaydedildi.")
                    driver.quit()
                    return True
                else:
                    print("❌ Login başarısız görünüyor. Tekrar deneyin.")
                    driver.quit()
                    return False
            else:
                print("❌ Cookie alınamadı. Login yapıldığından emin olun.")
                driver.quit()
                return False
                
        except Exception as e:
            print(f"❌ Login kurulumu sırasında hata: {e}")
            try:
                driver.quit()
            except:
                pass
            return False
