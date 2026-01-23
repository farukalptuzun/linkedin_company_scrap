"""
Runner script for Google Places lead scraper
Usage: python scrape_leads.py --sector "Technology" --location "Konya" --limit 20
"""
import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape company leads by sector and location using Google Places API"
    )
    parser.add_argument(
        "-s", "--sector",
        required=True,
        help='Sector keyword, e.g. "Technology"'
    )
    parser.add_argument(
        "-l", "--location",
        required=True,
        help='Location, e.g. "Konya"'
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of companies to scrape (default: 20)"
    )
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.abspath(__file__))
    scrapy_project_dir = os.path.join(root_dir, "company_data_scraper")

    if not os.path.isdir(scrapy_project_dir):
        print(
            f"Error: scrapy project directory not found: {scrapy_project_dir}",
            file=sys.stderr
        )
        return 2

    cmd = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "places_lead_spider",
        "-a",
        f"sector={args.sector}",
        "-a",
        f"location={args.location}",
        "-a",
        f"limit={args.limit}",
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"Working dir: {scrapy_project_dir}")
    print(f"Sector: {args.sector}")
    print(f"Location: {args.location}")
    print(f"Limit: {args.limit}")

    proc = subprocess.run(cmd, cwd=scrapy_project_dir)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
