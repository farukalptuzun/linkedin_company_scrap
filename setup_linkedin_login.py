#!/usr/bin/env python3
"""
LinkedIn Login Kurulum Scripti
İlk kurulumda bir kere çalıştırılır, LinkedIn'e login yapılır ve cookie'ler kaydedilir.
"""

import sys
import os

# Proje root'unu path'e ekle
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'company_data_scraper'))

from company_data_scraper.cookie_manager import LinkedInCookieManager

def main():
    print("\n" + "="*60)
    print("🔐 LinkedIn Login Kurulumu")
    print("="*60)
    print("\nBu script LinkedIn'e login yapmanızı sağlar.")
    print("Cookie'ler kaydedilir ve sonraki çalıştırmalarda otomatik kullanılır.")
    print("\n⚠️  Chrome görünür modda açılacak.")
    print("   LinkedIn'de login yapın, sonra script'e dönüp Enter'a basın.")
    print("="*60 + "\n")
    
    manager = LinkedInCookieManager()
    
    # Headless=False: Chrome görünür modda açılır
    success = manager.setup_login(headless=False)
    
    if success:
        print("\n✅ Kurulum tamamlandı!")
        print("Artık scrape_by_sector.py'yi çalıştırabilirsiniz:")
        print("   python3 scrape_by_sector.py --sector \"Technology\" --max-pages 3")
        return 0
    else:
        print("\n❌ Kurulum başarısız. Tekrar deneyin.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
