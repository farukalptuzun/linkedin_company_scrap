#!/usr/bin/env python3
"""
LLM-Based Sector Filtering Module

This module filters companies from MongoDB using Claude API to determine
if they belong to a specific sector based on their "about" descriptions.
"""

import os
import json
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()


class LLMSectorFilter:
    """Filter companies by sector using Claude API"""
    
    def __init__(self, mongo_uri: str = None, mongo_db: str = None, claude_api_key: str = None):
        """
        Initialize the LLM Sector Filter
        
        Args:
            mongo_uri: MongoDB connection URI (defaults to env var)
            mongo_db: MongoDB database name (defaults to env var)
            claude_api_key: Claude API key (defaults to env var)
        """
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI', 'mongodb://localhost:27017')
        self.mongo_db = mongo_db or os.getenv('MONGO_DB', 'leads_db')
        self.claude_api_key = claude_api_key or os.getenv('CLAUDE_API_KEY')
        
        if not self.claude_api_key:
            raise ValueError("CLAUDE_API_KEY environment variable is required")
        
        # Initialize MongoDB connection
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.source_collection = self.db['company_leads']
        
        # Initialize Claude API client
        self.claude_client = Anthropic(api_key=self.claude_api_key)
        
        # Rate limiting: Claude API allows 50 requests per minute for tier 1
        self.requests_per_minute = 50
        self.request_times = []
    
    def _rate_limit(self):
        """Rate limiting to avoid exceeding API limits"""
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            # Wait until we can make another request
            sleep_time = 60 - (now - self.request_times[0]) + 1
            if sleep_time > 0:
                print(f"Rate limit: waiting {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
        
        self.request_times.append(time.time())
    
    def _query_companies(self, sector_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query companies from MongoDB by sector
        
        Args:
            sector_name: Sector name to filter by
            limit: Maximum number of companies to return (None for all)
        
        Returns:
            List of company documents
        """
        query = {'sector': sector_name}
        
        # Only get companies that have an "about" field with content
        query['about'] = {'$exists': True, '$ne': '', '$ne': None}
        
        companies = list(self.source_collection.find(query).limit(limit) if limit else self.source_collection.find(query))
        
        print(f"Found {len(companies)} companies with sector '{sector_name}' and about descriptions")
        return companies
    
    def _prepare_batch_prompt(self, companies: List[Dict[str, Any]], sector_name: str) -> str:
        """
        Prepare prompt for Claude API with batch of companies
        
        Args:
            companies: List of company documents
            sector_name: Sector name to check against
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""Sen bir şirket sektör analiz uzmanısın. Aşağıdaki şirketlerin açıklamalarını inceleyip, her birinin "{sector_name}" sektörüne ait olup olmadığını belirle.

Her şirket için JSON formatında yanıt ver. Yanıt sadece geçerli bir JSON array olmalı, başka metin içermemeli.

Format:
[
  {{
    "company_name": "şirket adı",
    "belongs_to_sector": true/false,
    "confidence": 0.0-1.0,
    "reason": "kısa açıklama (Türkçe)"
  }},
  ...
]

Şirketler:
"""
        
        for company in companies:
            company_name = company.get('company_name', 'Unknown')
            about = company.get('about', '')
            website = company.get('website', '')
            
            prompt += f"\n---\n"
            prompt += f"Şirket: {company_name}\n"
            if website:
                prompt += f"Website: {website}\n"
            prompt += f"Açıklama: {about[:1000]}\n"  # Limit to 1000 chars per company
        
        prompt += "\n\nYanıtını sadece JSON array formatında ver, başka açıklama yapma:"
        
        return prompt
    
    def _call_claude_api(self, prompt: str, max_retries: int = 3) -> str:
        """
        Call Claude API with prompt
        
        Args:
            prompt: Prompt to send to Claude
            max_retries: Maximum number of retry attempts
        
        Returns:
            Response text from Claude
        """
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                message = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                # Extract text from response
                response_text = ""
                for content_block in message.content:
                    if content_block.type == "text":
                        response_text += content_block.text
                
                return response_text
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(f"Error calling Claude API (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to call Claude API after {max_retries} attempts: {e}")
    
    def _parse_llm_response(self, response_text: str, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse LLM response and match with companies
        
        Args:
            response_text: Response text from Claude API
            companies: Original list of companies
        
        Returns:
            List of results with LLM decisions
        """
        results = []
        
        try:
            # Try to extract JSON from response (might have markdown code blocks)
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            llm_results = json.loads(response_text)
            
            if not isinstance(llm_results, list):
                raise ValueError("Expected JSON array")
            
            # Create a mapping by company name for quick lookup
            company_map = {c.get('company_name', ''): c for c in companies}
            
            # Match LLM results with companies
            for llm_result in llm_results:
                company_name = llm_result.get('company_name', '')
                if company_name in company_map:
                    company = company_map[company_name]
                    results.append({
                        'company_name': company_name,
                        'sector': company.get('sector', ''),
                        'belongs_to_sector': llm_result.get('belongs_to_sector', False),
                        'confidence': llm_result.get('confidence', 0.5),
                        'reason': llm_result.get('reason', ''),
                        'about': company.get('about', ''),
                        'website': company.get('website', ''),
                        'location': company.get('location', ''),
                        'phone': company.get('phone', ''),
                        'emails': company.get('emails', []),
                        'filtered_at': datetime.utcnow(),
                    })
                else:
                    print(f"Warning: LLM result for '{company_name}' not found in companies list")
            
            # Handle companies that weren't in LLM response
            processed_names = {r['company_name'] for r in results}
            for company in companies:
                if company.get('company_name') not in processed_names:
                    print(f"Warning: Company '{company.get('company_name')}' not in LLM response")
                    # Add with default values
                    results.append({
                        'company_name': company.get('company_name', ''),
                        'sector': company.get('sector', ''),
                        'belongs_to_sector': False,
                        'confidence': 0.0,
                        'reason': 'LLM response missing',
                        'about': company.get('about', ''),
                        'website': company.get('website', ''),
                        'location': company.get('location', ''),
                        'phone': company.get('phone', ''),
                        'emails': company.get('emails', []),
                        'filtered_at': datetime.utcnow(),
                    })
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response text: {response_text[:500]}")
            # Return empty results or default values
            for company in companies:
                results.append({
                    'company_name': company.get('company_name', ''),
                    'sector': company.get('sector', ''),
                    'belongs_to_sector': False,
                    'confidence': 0.0,
                    'reason': f'JSON parse error: {str(e)}',
                    'about': company.get('about', ''),
                    'website': company.get('website', ''),
                    'location': company.get('location', ''),
                    'phone': company.get('phone', ''),
                    'emails': company.get('emails', []),
                    'filtered_at': datetime.utcnow(),
                })
        
        return results
    
    def _save_filtered_results(self, sector_name: str, results: List[Dict[str, Any]]):
        """
        Save filtered results to MongoDB collection
        
        Args:
            sector_name: Sector name (used for collection name)
            results: List of filtered results
        """
        # Create collection name: e.g., "technology" -> "tech_ai_filter"
        collection_name = self._get_collection_name(sector_name)
        collection = self.db[collection_name]
        
        # Create indexes
        try:
            collection.create_index([("company_name", 1), ("sector", 1)], unique=True)
            collection.create_index([("belongs_to_sector", 1)])
            collection.create_index([("confidence", -1)])
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
        
        # Upsert results
        saved_count = 0
        for result in results:
            filter_query = {
                'company_name': result['company_name'],
                'sector': result['sector']
            }
            
            update_query = {
                '$set': result
            }
            
            collection.update_one(filter_query, update_query, upsert=True)
            saved_count += 1
        
        print(f"Saved {saved_count} results to collection '{collection_name}'")
        
        # Print statistics
        belongs_count = sum(1 for r in results if r['belongs_to_sector'])
        print(f"Statistics:")
        print(f"  - Total companies: {len(results)}")
        print(f"  - Belongs to sector: {belongs_count}")
        print(f"  - Does not belong: {len(results) - belongs_count}")
        print(f"  - Average confidence: {sum(r['confidence'] for r in results) / len(results):.2f}")
    
    def _get_collection_name(self, sector_name: str) -> str:
        """
        Convert sector name to collection name
        
        Args:
            sector_name: Sector name (e.g., "technology", "Technology")
        
        Returns:
            Collection name (e.g., "tech_ai_filter")
        """
        sector_lower = sector_name.lower().strip()
        
        # Mapping for common sectors
        sector_mapping = {
            'technology': 'tech_ai_filter',
            'tech': 'tech_ai_filter',
            'bt': 'tech_ai_filter',
            'bilgi teknolojisi': 'tech_ai_filter',
            'finance': 'finance_ai_filter',
            'finans': 'finance_ai_filter',
            'healthcare': 'healthcare_ai_filter',
            'sağlık': 'healthcare_ai_filter',
            'manufacturing': 'manufacturing_ai_filter',
            'imalat': 'manufacturing_ai_filter',
            'retail': 'retail_ai_filter',
            'perakende': 'retail_ai_filter',
            'education': 'education_ai_filter',
            'eğitim': 'education_ai_filter',
        }
        
        if sector_lower in sector_mapping:
            return sector_mapping[sector_lower]
        
        # Default: convert to snake_case and add _ai_filter
        collection_name = sector_lower.replace(' ', '_').replace('-', '_')
        # Remove Turkish characters for collection name
        turkish_chars = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
        for turkish, english in turkish_chars.items():
            collection_name = collection_name.replace(turkish, english)
        
        return f"{collection_name}_ai_filter"
    
    def filter_by_sector(self, sector_name: str, batch_size: int = 15, limit: Optional[int] = None):
        """
        Filter companies by sector using LLM
        
        Args:
            sector_name: Sector name to filter by
            batch_size: Number of companies to process per batch
            limit: Maximum number of companies to process (None for all)
        """
        print(f"\n{'='*60}")
        print(f"Starting LLM Sector Filtering for: {sector_name}")
        print(f"{'='*60}\n")
        
        # Query companies
        companies = self._query_companies(sector_name, limit=limit)
        
        if not companies:
            print(f"No companies found with sector '{sector_name}' and about descriptions")
            return
        
        # Process in batches
        total_batches = (len(companies) + batch_size - 1) // batch_size
        all_results = []
        
        for batch_idx in range(0, len(companies), batch_size):
            batch = companies[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            
            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} companies)...")
            
            # Prepare prompt
            prompt = self._prepare_batch_prompt(batch, sector_name)
            
            # Call Claude API
            try:
                response_text = self._call_claude_api(prompt)
                
                # Parse response
                batch_results = self._parse_llm_response(response_text, batch)
                all_results.extend(batch_results)
                
                print(f"Batch {batch_num} completed: {len(batch_results)} results")
                
            except Exception as e:
                print(f"Error processing batch {batch_num}: {e}")
                # Add default results for this batch
                for company in batch:
                    all_results.append({
                        'company_name': company.get('company_name', ''),
                        'sector': company.get('sector', ''),
                        'belongs_to_sector': False,
                        'confidence': 0.0,
                        'reason': f'Error: {str(e)}',
                        'about': company.get('about', ''),
                        'website': company.get('website', ''),
                        'location': company.get('location', ''),
                        'phone': company.get('phone', ''),
                        'emails': company.get('emails', []),
                        'filtered_at': datetime.utcnow(),
                    })
        
        # Save all results
        if all_results:
            self._save_filtered_results(sector_name, all_results)
            print(f"\n✅ Filtering completed! Processed {len(all_results)} companies")
        else:
            print("\n⚠️  No results to save")
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Filter companies by sector using Claude API')
    parser.add_argument('--sector', type=str, required=True, help='Sector name to filter by')
    parser.add_argument('--batch-size', type=int, default=15, help='Number of companies per batch (default: 15)')
    parser.add_argument('--limit', type=int, default=None, help='Maximum number of companies to process (default: all)')
    parser.add_argument('--mongo-uri', type=str, default=None, help='MongoDB URI (default: from env)')
    parser.add_argument('--mongo-db', type=str, default=None, help='MongoDB database name (default: from env)')
    
    args = parser.parse_args()
    
    # Initialize filter
    filter_instance = LLMSectorFilter(
        mongo_uri=args.mongo_uri,
        mongo_db=args.mongo_db
    )
    
    try:
        # Run filtering
        filter_instance.filter_by_sector(
            sector_name=args.sector,
            batch_size=args.batch_size,
            limit=args.limit
        )
    finally:
        filter_instance.close()


if __name__ == '__main__':
    main()
