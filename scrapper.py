import asyncio
from wsgiref import headers
from utils import hash_url
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
# import tldextract
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
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
# Fix for Windows asyncio subprocess issues
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
import requests


load_dotenv()

open_router_key = os.getenv("OPEN_ROUTER_API_KEY")
ollama_link = os.getenv("OLLAMA_LINK")

ollama_key = os.getenv("OLLAMA_API_KEY")
open_router_link = os.getenv("OPEN_ROUTER_LINK")

crawl4ai_link = os.getenv("CRAWL4AI_LINK")
crawl4ai_token = os.getenv("CRAWL4AI_TOKEN")

contact_scorer = KeywordRelevanceScorer(
    keywords=[
        "contact", "about", "support", "location", 
        "reach-out", "email", "office", "headquarters",
        "team", "staff", "management"
    ],
    weight=0.8  # High weight because contact pages are usually buried 1-2 levels deep
)
keywords=[
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

extraction_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(
        provider="ollama/qwen3.5:397b-cloud",
        api_token= open_router_key,
        base_url=open_router_link,
    ),
    schema=Leads.model_json_schema(),  # ← pydantic v2 fix
    extraction_type="schema",
    instruction="""
        Extract only contact details on the website. Strip ads, nav etc.
    """
)

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

async def crawl(url,job_details):
    crawl_config = CrawlerRunConfig(
    only_text=True,
    excluded_tags=EXCLUDE_TAGS,
    excluded_selector=EXCLUDE_SELECTORS,
    markdown_generator=DefaultMarkdownGenerator(),  # ← pass an actual instance
    extraction_strategy=extraction_strategy,
    cache_mode="enabled",
    wait_for="body", # Wait for the page to load
    delay_before_return_html=2.0, # Give JS time to execute
    # This helps extract actual text instead of just HTML tags
    word_count_threshold=10,
    deep_crawl_strategy=BestFirstCrawlingStrategy(
    max_depth=2,
    include_external=False,
    url_scorer=contact_scorer,
    max_pages=15,
    ),
    scraping_strategy=LXMLWebScrapingStrategy(),
    stream=True
    
    )

    browser_config = BrowserConfig(
        headless=True,
        java_script_enabled=True,
        # Stealth mode is crucial for avoiding auth walls
        enable_stealth=True,
        avoid_ads=True ,
        # text_mode:True
    )
   
    async with AsyncWebCrawler(config=browser_config) as crawler:

        # Fetch sitemap
        sitemap_url = url.rstrip("/") + "/sitemap.xml"
        sitemap_result = await crawler.arun(url=sitemap_url)
        urls = re.findall(r"<loc>(.*?)</loc>", sitemap_result.html or "")
        urls = urls[:10]  # limit: 10

        if not urls:
            urls = [url]  # fallback to base URL

        print(f"🔍 Crawling {len(urls)} URLs from {url}")

        results = []
       
        for page_url in urls:
            async for result in await crawler.arun(url=page_url, config=crawl_config):
            # print(result[0])
                print(result)
                if result.success and result.extracted_content:
                    try:
                        data = json.loads(result.extracted_content)
                        
                        lead = {"job_id":job_details["job_id"],"job_name":job_details["job_name"],"lead_type":job_details["lead_type"],**data[0]}
                        if lead.get('email') or lead.get('phone'):
                            results.append(lead)
                        print(f"✅ Extracted: {result.extracted_content}")

                    except json.JSONDecodeError:
                        print(f"⚠️  Could not parse extraction for {page_url}")
                else:
                    print(f"❌ Failed: {page_url}")
        return results

class Scraper:
    def __init__(self, db):
        self.db = db
        

    async def scrape_urls(self, urls, target_schools,job_id,job_details):
        leads = []
        count = 0
        print("stop",target_schools)
        job_details = {"job_id":job_id,**job_details}
        lead_type = job_details.get("lead_type","")
        if lead_type == "people":
            instuction = """Extract any details in the url about the person like name,email,phone number. 
            if you can't get anything from the linked url extract the name and surname from the name field and use the linkedin url as the website field"""
        else:
            instuction = "Extract any contact details in the url about the company like name,email,phone number."
       
        print(instuction)
        
        for url in urls:
            if count >= target_schools:
                print("Reached target school count during scraping")
                break
            


            
            if not url.find("linkedin") == -1 :
                deepcrawl = None
            else:
                deepcrawl = {
                "type":"BestFirstCrawlingStrategy",
                "params":{
                    "max_depth":2,
                    "include_external":False,
                    "url_scorer":{
                        "type":"KeywordRelevanceScorer",
                        "params": {
                            "keywords": keywords,
                            "weight":0.8
                        }
                    },
                    "max_pages":15
                },
                }
            print("deep crawl strategy is",bool(deepcrawl))
         
            try:
                job_details = {"job_id":job_id,**job_details}
                response = requests.post(
                    crawl4ai_link, 
                    json={
                    "urls": [url],
    "browser_config":{
        "type":"BrowserConfig",
        "params":{
            "headless":True,
            "java_script_enabled":True,
            "enable_stealth":True,
            "avoid_ads":True,
            "text_mode":True
        }
    },
    "crawler_config": {
        "type": "CrawlerRunConfig",
        "params": {
            "only_text":True,
            "excluded_tags":EXCLUDE_TAGS,
            "excluded_selector": EXCLUDE_SELECTORS,
            "cache_mode": "enabled",
            "wait_for":"body",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "page_timeout":10000, # Wait for the page to load
            "delay_before_return_html":2.0,
            "word_count_threshold":10,
            
            # "scrapping_strategy":LXMLWebScrapingStrategy()
            # "stream":True,
            
            "deep_crawl_strategy":None,
            # deepcrawl,
            # {
            #     "type":"BestFirstCrawlingStrategy",
            #     "params":{
            #         "max_depth":2,
            #         "include_external":False,
            #         "url_scorer":{
            #             "type":"KeywordRelevanceScorer",
            #             "params": {
            #                 "keywords": keywords,
            #                 "weight":0.8
            #             }
            #         },
            #         "max_pages":15
            #     },
            #     },
            "extraction_strategy": {
                "type": "LLMExtractionStrategy",
                "params": {
                    "llm_config": {
                        "type": "LLMConfig",
                        "params": {
                            "provider": "openrouter/openai/gpt-oss-120b:free",
                            "api_token": open_router_key,
                            # "base_url": open_router_link
                        }
                    },
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "default": None
                            },
                            "phone": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
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
                    "instruction": instuction,
                    "apply_chunking": False,
                    "input_format": "markdown"
                }
            }
        }
    } 
               
                },
                 headers={'Authorization': 'Bearer ' + crawl4ai_token}
                )
                data = response.json()
                # print(len(data.get("results")))
                current_leads = None
                url_lead_added = False
                if bool(deepcrawl) :
                    for result in data.get('results'):
                        print("extracted_content:",result.get("extracted_content"), "type:",type(result.get("extracted_content")))
                        if len(result.get("extracted_content")) == 0:
                            print(result.get("extracted_content"))
                            print("no content extracted for this url, skipping...")
                            continue
                        content = json.loads(result.get("extracted_content"))[0]
                        print("content is",content, "type is", type(content))
                        
                        if content.get('error','') == False:
                            print("is not false")
                            has_phone = content.get('phone', "") is not None 
                            has_email = content.get('email', "") is not None
                            has_org = content.get("organization_name")
                            
                            # If found both phone and email
                            if has_phone and has_email and has_org:
                                # Remove previous dict if it exists
                                if current_leads is not None and url_lead_added:
                                    leads.pop()
                                # Add new complete dict and stop processing this URL
                                current_leads = {**job_details, **content}
                                leads.append(current_leads)
                                url_lead_added = True
                                break
                            
                            # If found only phone or email (but not both)
                            elif (has_phone or has_email) and has_org:
                                # Only add if we haven't added one for this URL yet
                                if not url_lead_added:
                                    current_leads = {**job_details, **content}
                                    leads.append(current_leads)
                                    url_lead_added = True

                    

                        

                else: 
                    for result in data.get('results'):
                        content = json.loads(result.get("extracted_content"))[0]
                        print("content is",content, "type is", type(content))
                        leads.append({**job_details, **content})
                        url_lead_added = True

                print("FINAL DATA",leads)
                print(f'link {count} + found {len(leads)}')

                if url_lead_added:
                    self.db.mark_url_visited(url,job_id)
                    count += 1

        


            except Exception as e:
                print(f"Error scraping {url}: {e}")
        print(f'url is {url} is done')

      

        return leads


# async def main():
#     # stuff = await crawl("https://www.santarama-miniland.co.za/",{"job_id":1,"job_name":"test1","lead_type":"person"}) 
#     # stuff = await crawl("https://www.dninvest.co.za",{"job_id":1,"job_name":"test1","lead_type":"person"})
#     stuff = await Scraper(Database()).scrape_urls(['https://bakertillyjhb.co.za/'],1,1,{"job_name":"test1","lead_type":"person"})
#     print(stuff)

# asyncio.run(main())


