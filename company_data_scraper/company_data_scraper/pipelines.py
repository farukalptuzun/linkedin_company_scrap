# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv


class CompanyDataScraperPipeline:
    def process_item(self, item, spider):
        return item


class MongoPipeline:
    """Pipeline to store items in MongoDB with upsert and email deduplication"""
    
    def __init__(self, mongo_uri, mongo_db, mongo_collection):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection
        self.client = None
        self.db = None
    
    @classmethod
    def from_crawler(cls, crawler):
        # Load environment variables
        load_dotenv()
        
        mongo_uri = crawler.settings.get('MONGO_URI') or os.getenv('MONGO_URI', 'mongodb://localhost:27017')
        mongo_db = crawler.settings.get('MONGO_DB') or os.getenv('MONGO_DB', 'leads_db')
        mongo_collection = crawler.settings.get('MONGO_COLLECTION') or os.getenv('MONGO_COLLECTION', 'company_leads')
        
        return cls(mongo_uri, mongo_db, mongo_collection)
    
    def open_spider(self, spider):
        """Open MongoDB connection when spider starts"""
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db[self.mongo_collection]
        
        # Create indexes for better performance
        # Remove sparse unique index on website (causes issues with multiple null values)
        # Use compound unique index on company_name + location instead
        
        # Get existing indexes
        existing_indexes = self.collection.list_indexes()
        index_names = [idx['name'] for idx in existing_indexes]
        
        # Drop old sparse unique index on website if exists
        if "website_1" in index_names:
            try:
                self.collection.drop_index("website_1")
                spider.logger.info("Dropped old website_1 index")
            except Exception as e:
                spider.logger.warning(f"Could not drop website_1 index: {e}")
        
        # Drop existing compound index if it exists (might not be unique)
        if "company_name_1_location_1" in index_names:
            try:
                self.collection.drop_index("company_name_1_location_1")
                spider.logger.info("Dropped old company_name_1_location_1 index")
            except Exception as e:
                spider.logger.warning(f"Could not drop company_name_1_location_1 index: {e}")
        
        # Create compound unique index for company_name + location
        try:
            self.collection.create_index([("company_name", 1), ("location", 1)], unique=True)
            spider.logger.info("Created unique index on company_name + location")
        except Exception as e:
            spider.logger.warning(f"Could not create unique index: {e}")
        
        # Non-unique index on website for faster queries (when website exists)
        try:
            self.collection.create_index([("website", 1)], sparse=True)
            spider.logger.info("Created sparse index on website")
        except Exception as e:
            spider.logger.warning(f"Could not create website index: {e}")
        
        spider.logger.info(f"Connected to MongoDB: {self.mongo_db}.{self.mongo_collection}")
    
    def close_spider(self, spider):
        """Close MongoDB connection when spider closes"""
        if self.client:
            self.client.close()
            spider.logger.info("MongoDB connection closed")
    
    def process_item(self, item, spider):
        """Process item and upsert to MongoDB"""
        adapter = ItemAdapter(item)
        
        # Skip if not a LeadItem
        if item.__class__.__name__ != 'LeadItem':
            return item
        
        # Prepare document
        website = adapter.get('website')
        # Convert empty string to None for sparse index compatibility
        if website == "":
            website = None
        
        doc = {
            'sector': adapter.get('sector'),
            'location': adapter.get('location'),
            'company_name': adapter.get('company_name'),
            'phone': adapter.get('phone'),
            'website': website,
            'about': adapter.get('about', ''),
            'source': adapter.get('source', 'google_places'),
            'created_at': adapter.get('created_at', datetime.utcnow()),
        }
        
        # Handle emails list
        emails = adapter.get('emails', [])
        if not isinstance(emails, list):
            emails = [emails] if emails else []
        
        # Determine upsert key
        company_name = doc.get('company_name')
        location = doc.get('location')
        
        if website:
            # Use website as unique key
            filter_query = {'website': website}
        else:
            # Use company_name + location as compound key
            filter_query = {
                'company_name': company_name,
                'location': location
            }
        
        # Upsert operation: update if exists, insert if not
        # Use $addToSet to add emails without duplicates
        update_query = {
            '$set': {
                'sector': doc['sector'],
                'location': doc['location'],
                'company_name': doc['company_name'],
                'phone': doc['phone'],
                'website': doc['website'],
                'about': doc['about'],
                'source': doc['source'],
                'updated_at': datetime.utcnow(),
            },
            '$addToSet': {
                'emails': {'$each': emails}
            }
        }
        
        # If this is a new document, set created_at
        existing = self.collection.find_one(filter_query)
        if not existing:
            update_query['$set']['created_at'] = doc['created_at']
        
        result = self.collection.update_one(
            filter_query,
            update_query,
            upsert=True
        )
        
        if result.upserted_id:
            spider.logger.info(f"Inserted new lead: {company_name} ({location})")
        else:
            spider.logger.info(f"Updated existing lead: {company_name} ({location})")
        
        return item
