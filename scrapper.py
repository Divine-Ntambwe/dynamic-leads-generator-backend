import asyncio
from wsgiref import headers
import os
from dotenv import load_dotenv
import json
from pydantic import BaseModel
from typing import Optional
import re
from urllib.parse import urlparse
from pathlib import Path
import sys
from database import Database
from concurrent.futures import ThreadPoolExecutor
import threading
import requests

# Fix for Windows asyncio subprocess issues
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

open_router_key = os.getenv("OPEN_ROUTER_API_KEY")
ollama_link = os.getenv("OLLAMA_LINK")
ollama_key = os.getenv("OLLAMA_API_KEY")
open_router_link = os.getenv("OPEN_ROUTER_LINK")
crawl4ai_link = os.getenv("CRAWL4AI_LINK")
crawl4ai_token = os.getenv("CRAWL4AI_TOKEN")

keywords = [
    "contact", "about", "support", "location", 
    "reach-out", "email", "office", "headquarters",
]

class Leads(BaseModel):
    email: Optional[list[str]] = None
    phone: Optional[list[str]] = None
    website: Optional[str] = None
    organization_name: Optional[str] = None
    job_position: Optional[str] = None
    notes: Optional[str] = None

EXCLUDE_TAGS = [
    "nav", "header", "aside", "script", "style",
    "noscript", "iframe", "svg", "button"
]

EXCLUDE_SELECTORS = ", ".join([
    ".ads", ".advertisement", ".social-share", ".share-buttons",
    ".follow-us", ".modal", ".popup", ".newsletter-signup",
    ".cookie-banner", ".cookie-consent", ".menu", ".breadcrumb",
    "#sidebar", "#comments", "#ad-slot"
])

class Scraper:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - ensures only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.db = Database()
        self.count = 0
        self.count_lock = threading.Lock()
        self._initialized = True

    def get_leads_count(self):
        with self.count_lock:
            print(self.count)
            return self.count

    def inc_count(self, num=1):
        with self.count_lock:
            self.count += num

    def _scrape_single_url(self, url, target_schools, job_id, job_details, lead_type, instruction):
        """Scrape a single URL and return leads. Designed for concurrent execution."""
        url_leads = []
        
        # Check if we've reached target count
        with self.count_lock:
            if self.count >= target_schools:
                print(f"Target count reached: {self.count}/{target_schools}")
                return url_leads
        
        # Determine deep crawl strategy
        if "linkedin" in url:
            deepcrawl = None
        else:
            deepcrawl = {
                "type": "BestFirstCrawlingStrategy",
                "params": {
                    "max_depth": 2,
                    "include_external": False,
                    "url_scorer": {
                        "type": "KeywordRelevanceScorer",
                        "params": {
                            "keywords": keywords,
                            "weight": 0.8
                        }
                    },
                    "max_pages": 15
                },
            }
        
        
        try:
            job_details_with_id = {"job_id": job_id, **job_details}
            response = requests.post(
                crawl4ai_link,
                json={
                    "urls": [url],
                    "browser_config": {
                        "type": "BrowserConfig",
                        "params": {
                            "headless": True,
                            "java_script_enabled": True,
                            "enable_stealth": True,
                            "avoid_ads": True,
                            "text_mode": True
                        }
                    },
                    "crawler_config": {
                        "type": "CrawlerRunConfig",
                        "params": {
                            "only_text": True,
                            "excluded_tags": EXCLUDE_TAGS,
                            "excluded_selector": EXCLUDE_SELECTORS,
                            "cache_mode": "enabled",
                            "wait_for": "body",
                            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                            "page_timeout": 30000,
                            "delay_before_return_html": 2.0,
                            "word_count_threshold": 10,
                            "deep_crawl_strategy": None,
                            "extraction_strategy": {
                                "type": "LLMExtractionStrategy",
                                "params": {
                                    "llm_config": {
                                        "type": "LLMConfig",
                                        "params": {
                                            "provider": "openrouter/openai/gpt-oss-120b:free",
                                            "api_token": open_router_key,
                                        }
                                    },
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "email": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "default": None
                                            },
                                            "phone": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "default": None
                                            },
                                            "website": {
                                                "type": "string",
                                                "default": None
                                            },
                                            "name": {
                                                "type": "string",
                                                "default": None
                                            },
                                            "organization_name": {
                                                "type": "string",
                                                "default": None
                                            },
                                            "job_position": {
                                                "type": "string",
                                                "default": None
                                            },
                                            "notes": {
                                                "type": "string",
                                                "default": None
                                            }
                                        }
                                    },
                                    "extraction_type": "schema",
                                    "instruction": instruction,
                                    "apply_chunking": False,
                                    "input_format": "markdown"
                                }
                            }
                        }
                    }
                },
                headers={'Authorization': 'Bearer ' + crawl4ai_token},
                timeout=120
            )
            
            data = response.json()
            current_leads = None
            url_lead_added = False
            
            if bool(deepcrawl):
                for result in data.get('results', []):
                    if len(result.get("extracted_content", "")) == 0:
                        print("No content extracted for this url, skipping...")
                        continue
                    
                    content = json.loads(result.get("extracted_content"))[0]
                    
                    if content.get('error', '') == False:
                        has_phone = content.get('phone', "") is not None
                        has_email = content.get('email', "") is not None
                        has_org = content.get("organization_name")
                        
                        # If found both phone and email
                        if has_phone and has_email and has_org:
                            # Remove previous dict if it exists
                            if current_leads is not None and url_lead_added:
                                url_leads.pop()
                            # Add new complete dict and stop processing this URL
                            current_leads = {**job_details_with_id, **content}
                            url_leads.append(current_leads)
                            url_lead_added = True
                            break
                        
                        # If found only phone or email (but not both)
                        elif (has_phone or has_email) and has_org:
                            # Only add if we haven't added one for this URL yet
                            if not url_lead_added:
                                current_leads = {**job_details_with_id, **content}
                                url_leads.append(current_leads)
                                url_lead_added = True
                    else:
                        continue
            else:
                for result in data.get('results', []):
                    content = json.loads(result.get("extracted_content"))[0]
                    url_leads.append({**job_details_with_id, **content})
                    url_lead_added = True
            
            if url_lead_added:
                self.db.mark_url_visited(url, job_id)
                self.inc_count()
            else:
                print(f"No leads extracted from {url} {content}")
            print(f"Total count: {self.get_leads_count()}")
        
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return url_leads
    
    def scrape_urls(self, urls, target_schools, job_id, job_details):
        """Scrape multiple URLs concurrently using ThreadPoolExecutor with 5 workers."""
        all_leads = []
        
        print(f"Starting concurrent scraping of {len(urls)} URLs with target: {target_schools}")
        job_details_prepared = {"job_id": job_id, **job_details}
        lead_type = job_details_prepared.get("lead_type", "")
        
        # Prepare instruction based on lead type
        if lead_type == "people":
            instruction = """Extract any details in the url about the person like name,email,phone number. 
            if you can't get anything from the linked url extract the name and surname from the name field and use the linkedin url as the website field
            always stick to the schema
            """
        else:
            instruction = "Extract any contact details in the url about the company like name,email,phone number. Always stick to the schema"
        
        # Use ThreadPoolExecutor with 5 workers for concurrent scraping
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all URLs to the executor
            futures = [
                executor.submit(
                    self._scrape_single_url,
                    url,
                    target_schools,
                    job_id,
                    job_details,
                    lead_type,
                    instruction
                )
                for url in urls
            ]
            
            # Collect results as they complete
            for future in futures:
                try:
                    url_leads = future.result()
                    all_leads.extend(url_leads)
                    
                    # Check if we've reached target count
                    with self.count_lock:
                        if self.count >= target_schools:
                            print(f"Target count reached: {self.count}/{target_schools}. Stopping further processing.")
                            break
                except Exception as e:
                    print(f"Error in concurrent execution: {e}")
        
        print(f"Concurrent scraping complete. Total leads found: {len(all_leads)}. Total URLs processed: {self.count}")
        self.count = 0
        return all_leads


# Example usage (commented out):
# scraper = Scraper()
# leads = scraper.scrape_urls(['https://example.com/'],10,1,{"job_name":"test","lead_type":"person"})
# print(leads)
