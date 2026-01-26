import argparse
import os
import re
import subprocess
import sys

# Import the geoId finder function from the spider
# We'll use a simplified version here to avoid circular imports
def get_geo_id_from_location(location: str) -> str:
    """
    Şehir adından LinkedIn GeoId'yi bulur.
    Bu fonksiyon spider'daki get_geo_id_from_location ile aynı mantığı kullanır.
    """
    if not location:
        return ""
    
    # LinkedIn GeoId mapping (spider'daki ile aynı)
    LINKEDIN_GEO_IDS = {
        # Türkiye Şehirleri
        'istanbul': '102424322',
        'ankara': '102424323',
        'izmir': '102424324',
        'bursa': '102424325',
        'antalya': '102424326',
        'adana': '102424327',
        'gaziantep': '102424328',
        'konya': '102424329',
        'kayseri': '102424330',
        'eskisehir': '102424331',
        'mersin': '102424332',
        'diyarbakir': '102424333',
        'samsun': '102424334',
        'denizli': '102424335',
        'sanliurfa': '102424336',
        'adapazari': '102424337',
        'malatya': '102424338',
        'erzurum': '102424339',
        'van': '102424340',
        'batman': '102424341',
        'elazig': '102424342',
        'izmit': '102424343',
        'manisa': '102424344',
        'sivas': '102424345',
        'gebze': '102424346',
        'balikesir': '102424347',
        'tarsus': '102424348',
        'kutahya': '102424349',
        'trabzon': '102424350',
        'corum': '102424351',
        'kocaeli': '102424352',
        'osmaniye': '102424353',
        'cayirova': '102424354',
        'mugla': '102424355',
        # Yurtdışı Popüler Şehirler
        'london': '90009449',
        'paris': '105015875',
        'berlin': '106967730',
        'amsterdam': '100565486',
        'new york': '103644278',
        'san francisco': '103748137',
        'los angeles': '102748796',
        'tokyo': '103323778',
        'sydney': '105117694',
        'dubai': '102460086',
    }
    
    # Normalize: lowercase, strip
    location_normalized = location.lower().strip()
    
    # Direkt mapping kontrolü
    if location_normalized in LINKEDIN_GEO_IDS:
        return LINKEDIN_GEO_IDS[location_normalized]
    
    # Türkçe karakterleri normalize et
    turkish_chars = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
    location_normalized_no_turkish = location_normalized
    for turkish, english in turkish_chars.items():
        location_normalized_no_turkish = location_normalized_no_turkish.replace(turkish, english)
    
    if location_normalized_no_turkish in LINKEDIN_GEO_IDS:
        return LINKEDIN_GEO_IDS[location_normalized_no_turkish]
    
    # Partial match
    location_first_word = location_normalized.split(',')[0].split()[0] if location_normalized else ""
    if location_first_word and location_first_word in LINKEDIN_GEO_IDS:
        return LINKEDIN_GEO_IDS[location_first_word]
    
    # Tüm mapping'de partial match ara
    for city, geo_id in LINKEDIN_GEO_IDS.items():
        if city in location_normalized or location_normalized in city:
            return geo_id
    
    return ""


def _safe_slug(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text or "sector"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape LinkedIn companies by sector, location, and limit (root runner).")
    parser.add_argument("-s", "--sector", required=True, help='Sector keyword, e.g. "Technology"')
    parser.add_argument("-l", "--location", required=False, help='Location name (e.g. "Istanbul") - Auto-detects geo_id if not provided')
    parser.add_argument("--geo-id", required=False, help='LinkedIn geoId for location (e.g. "102424322" for Istanbul). Auto-detected from --location if not provided.')
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of companies to scrape (default: 20)")
    parser.add_argument("--max-pages", default="20", help="Max search pages to crawl per sector ID (default: 20)")
    args = parser.parse_args()
    
    # Auto-detect geo_id from location if location is provided but geo_id is not
    if args.location and not args.geo_id:
        auto_geo_id = get_geo_id_from_location(args.location)
        if auto_geo_id:
            args.geo_id = auto_geo_id
            print(f"✅ Auto-detected geo_id '{auto_geo_id}' for location '{args.location}'")
        else:
            print(f"⚠️  Could not auto-detect geo_id for location '{args.location}'")
            print("   Location filtering may not work. Please provide --geo-id manually.")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    scrapy_project_dir = os.path.join(root_dir, "company_data_scraper")

    if not os.path.isdir(scrapy_project_dir):
        print(f"Error: scrapy project directory not found: {scrapy_project_dir}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "sector_based_scraper",
        "-a",
        f"sector={args.sector}",
        "-a",
        f"limit={args.limit}",
        "-a",
        f"max_pages={args.max_pages}",
    ]
    
    # Add location if provided (for display purposes, but geo_id is preferred)
    if args.location:
        cmd.extend(["-a", f"location={args.location}"])
    
    # Add geo_id if provided (this is the correct way to filter by location)
    if args.geo_id:
        cmd.extend(["-a", f"geo_id={args.geo_id}"])

    print(f"Running: {' '.join(cmd)}")
    print(f"Working dir: {scrapy_project_dir}")
    print(f"Sector: {args.sector}")
    if args.geo_id:
        print(f"Geo ID: {args.geo_id} (location filter)")
    if args.location:
        if args.geo_id:
            print(f"Location: {args.location} (geo_id auto-detected)")
        else:
            print(f"Location: {args.location} (no geo_id found - location filtering disabled)")
    print(f"Limit: {args.limit} companies")
    print(f"Max Pages: {args.max_pages}")
    print("Note: Data will be saved to MongoDB (configured in settings.py)")

    proc = subprocess.run(cmd, cwd=scrapy_project_dir)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

