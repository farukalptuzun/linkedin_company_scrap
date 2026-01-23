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
    parser.add_argument("-l", "--location", required=True, help='Location, e.g. "Istanbul"')
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of companies to scrape (default: 20)")
    parser.add_argument("--max-pages", default="3", help="Max search pages to crawl (default: 3)")
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
        f"location={args.location}",
        "-a",
        f"limit={args.limit}",
        "-a",
        f"max_pages={args.max_pages}",
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"Working dir: {scrapy_project_dir}")
    print(f"Sector: {args.sector}")
    print(f"Location: {args.location}")
    print(f"Limit: {args.limit} companies")
    print(f"Max Pages: {args.max_pages}")
    print("Note: Data will be saved to MongoDB (configured in settings.py)")

    proc = subprocess.run(cmd, cwd=scrapy_project_dir)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

