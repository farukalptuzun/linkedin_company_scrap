import argparse
import os
import re
import subprocess
import sys


def _safe_slug(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text or "sector"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape LinkedIn companies by sector, location, and limit (root runner).")
    parser.add_argument("-s", "--sector", required=True, help='Sector keyword, e.g. "Technology"')
    parser.add_argument("-l", "--location", required=False, help='Location name (e.g. "Istanbul") - NOTE: Use --geo-id for proper location filtering')
    parser.add_argument("--geo-id", required=False, help='LinkedIn geoId for location (e.g. "106693272" for Istanbul). Get this from LinkedIn URL when filtering by location in UI.')
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of companies to scrape (default: 20)")
    parser.add_argument("--max-pages", default="20", help="Max search pages to crawl per sector ID (default: 20)")
    args = parser.parse_args()

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
        print(f"Location: {args.location} (display only - use --geo-id for filtering)")
    print(f"Limit: {args.limit} companies")
    print(f"Max Pages: {args.max_pages}")
    print("Note: Data will be saved to MongoDB (configured in settings.py)")
    if args.location and not args.geo_id:
        print("⚠️  WARNING: Location name provided but no geo_id. Location filtering may not work correctly.")
        print("   To get geo_id: Open LinkedIn, filter by location, copy companyHqGeo value from URL")
        print("   Example: companyHqGeo=%5B%22102424322%22%5D → geo_id=102424322 (Istanbul)")

    proc = subprocess.run(cmd, cwd=scrapy_project_dir)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

