# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from datetime import datetime


class CompanyDataScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class LeadItem(scrapy.Item):
    """Item for company leads scraped from Google Places"""
    sector = scrapy.Field()
    location = scrapy.Field()
    company_name = scrapy.Field()
    phone = scrapy.Field()
    emails = scrapy.Field()  # List of email addresses
    website = scrapy.Field()
    source = scrapy.Field()  # e.g., "google_places"
    about = scrapy.Field()  # Company description from LinkedIn or website
    created_at = scrapy.Field()
