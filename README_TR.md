# LinkedIn Şirket Verisi Çekme Sistemi - Detaylı Analiz Raporu

## 📋 İçindekiler

1. [Proje Genel Bakış](#proje-genel-bakış)
2. [Proje Yapısı](#proje-yapısı)
3. [Sistem Nasıl Çalışıyor?](#sistem-nasıl-çalışıyor)
4. [Spider'ların Detaylı Analizi](#spiderların-detaylı-analizi)
5. [Çekilen Veriler](#çekilen-veriler)
6. [Gereksinimler ve Kurulum](#gereksinimler-ve-kurulum)
7. [Kullanım Kılavuzu](#kullanım-kılavuzu)
8. [Teknik Detaylar](#teknik-detaylar)
9. [Önemli Notlar ve Sınırlamalar](#önemli-notlar-ve-sınırlamalar)

---

## 🎯 Proje Genel Bakış

Bu proje, LinkedIn platformundan şirket verilerini otomatik olarak çekmek için geliştirilmiş bir **Scrapy** tabanlı web scraping sistemidir. Sistem, iki aşamalı bir yaklaşım kullanarak:

1. **İlk Aşama**: LinkedIn şirket dizininden binlerce şirket ismi ve URL'lerini toplar
2. **İkinci Aşama**: Belirttiğiniz şirketlerin detaylı profil bilgilerini çeker

### Projenin Amacı
- LinkedIn'deki şirket dizininden toplu veri çekme
- Belirli şirketlerin detaylı profil bilgilerini otomatik olarak toplama
- Araştırma, analiz ve iş geliştirme amaçlı veri toplama

---

## 📁 Proje Yapısı

```
LinkedIn-Company-Data-Scraping-System/
├── company_data_scraper/              # Ana proje klasörü
│   ├── company_data_scraper/          # Scrapy proje modülü
│   │   ├── spiders/                   # Spider'lar (veri çekme botları)
│   │   │   ├── linkedin_directory_scraper.py    # Şirket dizini çekici
│   │   │   └── company_profile_scraper.py       # Şirket profil çekici
│   │   ├── items.py                   # Veri modelleri (şu an kullanılmıyor)
│   │   ├── pipelines.py               # Veri işleme pipeline'ları
│   │   ├── middlewares.py             # Middleware'ler (istek/yanıt işleme)
│   │   ├── settings.py                # Scrapy ayarları
│   │   └── __init__.py
│   ├── scrapy.cfg                     # Scrapy konfigürasyon dosyası
│   ├── directorydata.json             # Çekilen şirket dizini verileri (198K+ satır)
│   └── company_profile.json           # Çekilen şirket profil verileri
├── README.md                           # İngilizce dokümantasyon
└── LICENSE                             # Lisans dosyası
```

---

## ⚙️ Sistem Nasıl Çalışıyor?

### Genel Çalışma Mantığı

Proje, **iki ayrı spider** kullanarak çalışır:

#### 1️⃣ LinkedIn Directory Scraper (Dizin Çekici)
- LinkedIn'in şirket dizin sayfasını tarar
- Google Cache üzerinden erişim sağlar (anti-bot korumasını aşmak için)
- A'dan Z'ye tüm harfler için dizin sayfalarını ziyaret eder
- Her sayfadaki şirket isimlerini ve LinkedIn URL'lerini toplar
- Sonuçları `directorydata.json` dosyasına kaydeder

#### 2️⃣ Company Profile Scraper (Profil Çekici)
- `directorydata.json` dosyasını okur
- Kullanıcının belirttiği şirket isimlerini arar
- Bulunan şirketlerin LinkedIn URL'lerini alır
- Her şirket profil sayfasını ziyaret eder
- Detaylı şirket bilgilerini çıkarır
- Sonuçları `company_profile.json` dosyasına kaydeder

### Veri Akışı

```
LinkedIn Dizin Sayfası
    ↓
[linkedin_directory_scraper.py]
    ↓
directorydata.json (Şirket İsimleri + URL'ler)
    ↓
[company_profile_scraper.py]
    ↓
company_profile.json (Detaylı Şirket Bilgileri)
```

---

## 🕷️ Spider'ların Detaylı Analizi

### 1. LinkedIn Directory Scraper (`linkedin_directory_scraper.py`)

#### Ne Yapar?
LinkedIn'in şirket dizininden tüm şirket isimlerini ve URL'lerini toplar.

#### Nasıl Çalışır?

**Başlangıç URL'leri:**
- Ana dizin sayfası: `https://webcache.googleusercontent.com/search?q=cache:https://www.linkedin.com/directory/companies`
- A-Z harfleri için 26 farklı sayfa
- "More" kategorisi için ek bir sayfa
- **Toplam 27 farklı sayfa** taranır

**Çalışma Adımları:**

1. **İlk Parse (`parse` metodu):**
   - Ana sayfadaki öne çıkan şirketleri (`featured_company_listings`) çeker
   - Şirket isimlerini ve URL'lerini bir dictionary'ye kaydeder
   - İlk harf sayfasına (A harfi) geçiş yapar

2. **Harf Sayfalarını Parse Etme (`parse_response` metodu):**
   - Her harf için (A, B, C, ..., Z, More) sayfayı ziyaret eder
   - Sayfadaki tüm şirket listelerini (`listings__entry-link`) çeker
   - Şirket ismi → URL eşleştirmesi yapar
   - Bir sonraki harf sayfasına geçer

**Çıktı Formatı:**
```json
[
    {
        "Amazon": "https://www.linkedin.com/company/amazon?trk=companies_directory",
        "Google": "https://www.linkedin.com/company/google?trk=companies_directory",
        "Microsoft": "https://www.linkedin.com/company/microsoft?trk=companies_directory",
        ...
    }
]
```

**Önemli Notlar:**
- Google Cache kullanılıyor (LinkedIn'in doğrudan erişimini engellemek için)
- Yaklaşık **200,000+ şirket** verisi çekilebilir
- Her harf için ayrı sayfa ziyaret edilir

---

### 2. Company Profile Scraper (`company_profile_scraper.py`)

#### Ne Yapar?
Belirttiğiniz şirketlerin detaylı profil bilgilerini çeker.

#### Nasıl Çalışır?

**Başlangıç Ayarları:**
```python
desired_company_names = ["OpenAI", "Microsoft"]  # İstediğiniz şirketleri buraya ekleyin
input_file = 'directorydata.json'  # Şirket URL'lerinin bulunduğu dosya
```

**Çalışma Adımları:**

1. **URL Bulma (`get_url_by_company_name` fonksiyonu):**
   - `directorydata.json` dosyasını okur
   - `desired_company_names` listesindeki şirketleri arar
   - Bulunan şirketlerin LinkedIn URL'lerini toplar
   - Eğer şirket bulunamazsa hata verir

2. **Profil Sayfalarını Ziyaret Etme (`start_requests` metodu):**
   - Bulunan URL'lerden ilkini alır
   - Scrapy Request oluşturur ve parse işlemini başlatır

3. **Veri Çıkarma (`parse_response` metodu):**
   - Her şirket profil sayfasından **16 farklı veri** çıkarır:
     - Şirket adı
     - LinkedIn takipçi sayısı
     - Şirket logosu URL'i
     - Hakkında bölümü
     - Çalışan sayısı
     - Web sitesi
     - Sektör
     - Şirket büyüklüğü
     - Genel merkez konumu
     - Şirket tipi
     - Kuruluş yılı
     - Uzmanlık alanları
     - Fonlama bilgileri
     - Toplam fonlama turu sayısı
     - Fonlama seçeneği
     - Son fonlama turu tarihi

**Çıktı Formatı:**
```json
[
    {
        "company_name": "OpenAI",
        "linkedin_followers_count": 2610704,
        "company_logo_url": "https://media.licdn.com/...",
        "about_us": "OpenAI is an AI research...",
        "num_of_employees": 1230,
        "website": "https://openai.com/",
        "industry": "Research Services",
        "company_size_approx": "201-500",
        "headquarters": "San Francisco, CA",
        "type": "Partnership",
        "founded": "2015",
        "specialties": "artificial intelligence and machine learning",
        "funding": "not-found",
        "funding_total_rounds": 10,
        "funding_option": "Secondary market",
        "last_funding_round": "Sep 14, 2023"
    }
]
```

**CSS/XPath Seçicileri:**
- Şirket adı: `.top-card-layout__entity-info h1`
- Takipçi sayısı: XPath ile `//h3[contains(@class, "top-card-layout__first-subline")]`
- Logo: `div.top-card-layout__entity-image-container img::attr(data-delayed-url)`
- Hakkında: `.core-section-container__content p`
- Detaylar: `.core-section-container__content .mb-2` (çoklu element)

---

## 📊 Çekilen Veriler

### Directory Scraper'dan Gelen Veriler

| Veri Tipi | Açıklama | Örnek |
|-----------|----------|-------|
| Şirket İsmi | LinkedIn'deki şirket adı | "Microsoft" |
| LinkedIn URL | Şirketin LinkedIn profil sayfası URL'i | "https://www.linkedin.com/company/microsoft" |

**Toplam Veri Miktarı:** ~200,000 şirket

---

### Profile Scraper'dan Gelen Veriler

| # | Veri Alanı | Açıklama | Veri Tipi | Örnek Değer |
|---|------------|----------|-----------|-------------|
| 1 | `company_name` | Şirketin resmi adı | String | "OpenAI" |
| 2 | `linkedin_followers_count` | LinkedIn'deki takipçi sayısı | Integer | 2610704 |
| 3 | `company_logo_url` | Şirket logosunun URL'i | String | "https://media.licdn.com/..." |
| 4 | `about_us` | Şirket hakkında açıklama metni | String | "OpenAI is an AI research..." |
| 5 | `num_of_employees` | Çalışan sayısı | Integer/String | 1230 |
| 6 | `website` | Şirketin resmi web sitesi | String | "https://openai.com/" |
| 7 | `industry` | Sektör bilgisi | String | "Research Services" |
| 8 | `company_size_approx` | Şirket büyüklüğü aralığı | String | "201-500" |
| 9 | `headquarters` | Genel merkez konumu | String | "San Francisco, CA" |
| 10 | `type` | Şirket tipi | String | "Partnership" |
| 11 | `founded` | Kuruluş yılı | String | "2015" |
| 12 | `specialties` | Uzmanlık alanları | String | "artificial intelligence..." |
| 13 | `funding` | Fonlama bilgisi | String | "not-found" |
| 14 | `funding_total_rounds` | Toplam fonlama turu sayısı | Integer | 10 |
| 15 | `funding_option` | Fonlama seçeneği | String | "Secondary market" |
| 16 | `last_funding_round` | Son fonlama turu tarihi | String | "Sep 14, 2023" |

**Toplam Veri Alanı:** 16 farklı parametre

---

## 🔧 Gereksinimler ve Kurulum

### Sistem Gereksinimleri

- **Python:** 3.7 veya üzeri
- **İşletim Sistemi:** Windows, macOS, Linux
- **İnternet Bağlantısı:** Aktif internet bağlantısı gerekli

### Python Paketleri

Proje şu Python paketlerine ihtiyaç duyar:

```python
scrapy>=2.0.0          # Web scraping framework'ü
requests                # HTTP istekleri için (opsiyonel)
itemadapter            # Scrapy item adapter'ı
```

### Kurulum Adımları

#### 1. Projeyi İndirin
```bash
cd /Users/faruk/Desktop/Tarvina/linkedin_scraping/LinkedIn-Company-Data-Scraping-System
```

#### 2. Python Sanal Ortamı Oluşturun (Önerilir)
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux için
# veya
venv\Scripts\activate      # Windows için
```

#### 3. Gerekli Paketleri Yükleyin
```bash
pip install scrapy requests itemadapter
```

#### 4. Proje Klasörüne Gidin
```bash
cd company_data_scraper
```

---

## 🚀 Kullanım Kılavuzu

### Adım 1: Şirket Dizini Verilerini Çekme

İlk olarak, LinkedIn'deki tüm şirket isimlerini ve URL'lerini çekmeniz gerekir:

```bash
cd company_data_scraper
scrapy crawl linkedin_directory_scraper -O directorydata.json
```

**Ne Olur?**
- LinkedIn şirket dizini taranır
- A-Z harfleri ve "More" kategorisi için tüm sayfalar ziyaret edilir
- Şirket isimleri ve URL'leri `directorydata.json` dosyasına kaydedilir
- İşlem birkaç saat sürebilir (200K+ şirket)

**Çıktı:** `directorydata.json` dosyası oluşturulur

---

### Adım 2: Belirli Şirketlerin Profil Bilgilerini Çekme

#### 2.1 Şirket İsimlerini Belirleyin

`company_profile_scraper.py` dosyasını açın ve `desired_company_names` listesini düzenleyin:

```python
desired_company_names = ["OpenAI", "Microsoft", "Google", "Apple"]  # İstediğiniz şirketleri ekleyin
```

**Önemli:** Şirket isimlerinin yazımına dikkat edin! `directorydata.json` dosyasındaki isimlerle tam olarak eşleşmelidir.

#### 2.2 Profil Verilerini Çekin

```bash
scrapy crawl company_profile_scraper -O company_profile.json
```

**Ne Olur?**
- `directorydata.json` dosyası okunur
- Belirttiğiniz şirket isimleri aranır
- Bulunan şirketlerin LinkedIn URL'leri alınır
- Her şirket profil sayfası ziyaret edilir
- Detaylı bilgiler çıkarılır ve `company_profile.json` dosyasına kaydedilir

**Çıktı:** `company_profile.json` dosyası oluşturulur

---

### Alternatif Çıktı Formatları

Scrapy, farklı formatlarda çıktı almanıza izin verir:

```bash
# JSON formatında
scrapy crawl company_profile_scraper -O company_profile.json

# CSV formatında
scrapy crawl company_profile_scraper -O company_profile.csv

# XML formatında
scrapy crawl company_profile_scraper -O company_profile.xml
```

---

## 🧭 Sektör Bazlı Tek Pipeline Kullanımı (Root'tan)

Bu akışta **sektör verilir**, sistem LinkedIn aramasından şirketleri bulur ve **aynı koşuda** şirket profil detaylarını çekip tek bir çıktıya yazar.

### Çalıştırma

Root dizinde:

```bash
python scrape_by_sector.py --sector "Technology"
```

Opsiyonel olarak arama sayfası sayısını sınırlamak için:

```bash
python scrape_by_sector.py --sector "Technology" --max-pages 3
```

### Çıktı

Her sektör için ayrı dosya üretilir:
- `technology_companies.json`
- `finance_companies.json`
- `healthcare_companies.json`

---

## 🔍 Teknik Detaylar

### Scrapy Ayarları (`settings.py`)

```python
BOT_NAME = "company_data_scraper"
USER_AGENT = "Mozilla/5.0 (Linux; Android 11; Redmi Note 8 Pro) AppleWebKit/537.36..."
ROBOTSTXT_OBEY = False  # robots.txt kurallarını görmezden gel
FEED_EXPORT_ENCODING = "utf-8"  # Türkçe karakter desteği
```

**Önemli Ayarlar:**
- **USER_AGENT:** Tarayıcı kimliği (bot olarak algılanmamak için)
- **ROBOTSTXT_OBEY:** False olarak ayarlanmış (LinkedIn'in robots.txt kurallarını görmezden gelir)
- **FEED_EXPORT_ENCODING:** UTF-8 karakter kodlaması

### Google Cache Kullanımı

Proje, LinkedIn'in anti-bot korumasını aşmak için **Google Cache** kullanır:

```
Normal URL: https://www.linkedin.com/directory/companies
Cache URL:  https://webcache.googleusercontent.com/search?q=cache:https://www.linkedin.com/directory/companies
```

**Avantajları:**
- LinkedIn'in doğrudan erişim kısıtlamalarını aşar
- Daha az bot tespiti riski
- Daha stabil erişim

**Dezavantajları:**
- Veriler güncel olmayabilir (cache'lenmiş versiyonlar)
- Google Cache'in kendi kısıtlamaları olabilir

### Veri Çıkarma Yöntemleri

#### CSS Seçicileri
```python
response.css('.top-card-layout__entity-info h1::text').get()
```

#### XPath Seçicileri
```python
response.xpath('//h3[contains(@class, "top-card-layout__first-subline")]/span/following-sibling::text()').get()
```

#### Regex Kullanımı
```python
re.findall(r'\d{1,3}(?:,\d{3})*', text)  # Sayıları çıkarmak için
```

### Hata Yönetimi

Proje, eksik veriler için `try-except` blokları kullanır:

```python
try:
    # Veri çıkarma işlemi
except IndexError:
    print("Error: *****Skipped index, as some details are missing*********")
except Exception as e:
    print(f"Error occurred: {e}")
```

Eksik veriler için `"not-found"` değeri kullanılır.

---

## ⚠️ Önemli Notlar ve Sınırlamalar

### Yasal ve Etik Uyarılar

1. **LinkedIn Kullanım Şartları:**
   - LinkedIn'in Terms of Service'ini ihlal edebilir
   - Otomatik veri çekme LinkedIn tarafından yasaklanmış olabilir
   - Kullanımınızın sorumluluğu size aittir

2. **Rate Limiting:**
   - LinkedIn, çok fazla istek yaparsanız IP adresinizi engelleyebilir
   - İstekler arasında gecikme eklemeniz önerilir

3. **Veri Kullanımı:**
   - Çekilen verileri ticari amaçlarla kullanmadan önce yasal danışmanlık alın
   - Kişisel verilerin korunması yasalarına (GDPR, KVKK) dikkat edin

### Teknik Sınırlamalar

1. **LinkedIn HTML Yapısı Değişiklikleri:**
   - LinkedIn, sayfa yapısını değiştirebilir
   - CSS/XPath seçicileri çalışmayabilir
   - Kodun güncellenmesi gerekebilir

2. **Google Cache Bağımlılığı:**
   - Google Cache'e erişim kısıtlanabilir
   - Cache'lenmiş veriler güncel olmayabilir

3. **Veri Doğruluğu:**
   - Bazı şirketler eksik bilgilere sahip olabilir
   - "not-found" değerleri görülebilir
   - Verileri manuel olarak doğrulamanız önerilir

4. **Performans:**
   - Directory scraper uzun sürebilir (saatler)
   - Çok sayıda şirket için profil scraper yavaş olabilir
   - İnternet hızınıza bağlıdır

### Önerilen İyileştirmeler

1. **Rate Limiting Ekleyin:**
```python
# settings.py'ye ekleyin
DOWNLOAD_DELAY = 2  # İstekler arası 2 saniye bekle
RANDOMIZE_DOWNLOAD_DELAY = True  # Rastgele gecikme
```

2. **Proxy Kullanımı:**
   - IP engellemelerini önlemek için proxy rotasyonu ekleyin

3. **User-Agent Rotasyonu:**
   - Farklı tarayıcı kimlikleri kullanın

4. **Veritabanı Entegrasyonu:**
   - JSON yerine veritabanına kaydetme
   - Daha kolay sorgulama ve analiz

5. **Hata Loglama:**
   - Detaylı log dosyaları oluşturun
   - Başarısız istekleri kaydedin

---

## 📝 Örnek Kullanım Senaryoları

### Senaryo 1: Tek Bir Şirket Hakkında Bilgi Toplama

```python
# company_profile_scraper.py içinde
desired_company_names = ["OpenAI"]
```

```bash
scrapy crawl company_profile_scraper -O openai_profile.json
```

### Senaryo 2: Belirli Sektördeki Şirketleri Analiz Etme

1. Directory scraper'ı çalıştırın
2. `directorydata.json` dosyasını açın
3. İlgilendiğiniz sektördeki şirketleri bulun
4. `desired_company_names` listesine ekleyin
5. Profile scraper'ı çalıştırın

### Senaryo 3: Toplu Veri Analizi

1. Tüm şirket dizinini çekin
2. İstediğiniz şirketleri seçin
3. Profil verilerini çekin
4. JSON dosyasını pandas ile analiz edin:

```python
import pandas as pd
import json

with open('company_profile.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)
print(df.describe())
print(df['industry'].value_counts())
```

---

## 🐛 Sorun Giderme

### Sorun: "No company URLs found"

**Çözüm:**
- `directorydata.json` dosyasının mevcut olduğundan emin olun
- Şirket isimlerinin yazımını kontrol edin
- JSON dosyasının formatını kontrol edin

### Sorun: "Error: JSON file not found"

**Çözüm:**
- Önce directory scraper'ı çalıştırın
- Dosya yolunun doğru olduğundan emin olun

### Sorun: Veriler çekilmiyor veya "not-found" geliyor

**Çözüm:**
- LinkedIn sayfa yapısı değişmiş olabilir
- CSS/XPath seçicilerini güncellemeniz gerekebilir
- Google Cache'e erişim sorunu olabilir

### Sorun: IP adresim engellendi

**Çözüm:**
- İstekler arası gecikme ekleyin (`DOWNLOAD_DELAY`)
- Proxy kullanın
- Farklı bir ağdan deneyin

---

## 📚 Ek Kaynaklar

- [Scrapy Dokümantasyonu](https://docs.scrapy.org/)
- [CSS Seçicileri Rehberi](https://www.w3schools.com/cssref/css_selectors.asp)
- [XPath Rehberi](https://www.w3schools.com/xml/xpath_intro.asp)
- [LinkedIn Terms of Service](https://www.linkedin.com/legal/user-agreement)

---

## 📞 Destek ve Katkıda Bulunma

Bu proje açık kaynaklıdır ve katkılarınızı bekler. Sorunlarınız veya önerileriniz için:

1. GitHub Issues açın
2. Pull Request gönderin
3. Dokümantasyonu iyileştirin

---

## 📄 Lisans

Proje lisans bilgileri için `LICENSE` dosyasına bakın.

---

**Son Güncelleme:** 2024
**Versiyon:** 1.0
**Dil:** Python 3.7+
**Framework:** Scrapy 2.0+

---

*Bu dokümantasyon, projenin detaylı analizi ve kullanım kılavuzunu içermektedir. Teknik sorularınız için Scrapy dokümantasyonunu inceleyebilirsiniz.*
