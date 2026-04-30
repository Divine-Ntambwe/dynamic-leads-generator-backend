import asyncio
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
    "team", "staff", "management"
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
        api_token= os.getenv("OLLAMA_API_KEY"),
        base_url="https://unsingable-streakedly-letha.ngrok-free.dev",
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
        results = []
        count = 0
        print("stop",target_schools)
       
        
        
        for i in range(0,len(urls),2):   

            if count == target_schools:
                print("Reached target school count during scraping")
                break
            count+=2 
            
            link1 = urls[i]
            if i+1 >= len(urls):
                link2 = ""
            else:
                link2 = urls[i+1]
                
            both_links = [link1,link2]
            if both_links.count(""):
                both_links.pop(both_links.index(""))
            print(both_links)
            # continue
            deepcrawl = None
            if link1.find("linkedin") == -1 or link2.find("linkedin"):
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

            try:
                job_details = {"job_id":job_id,**job_details}
                response = requests.post(
                    'https://crawl4ai-production-40e2.up.railway.app/crawl', 
                    json={
                    "urls": both_links,
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
            "delay_before_return_html":2.0,
            "word_count_threshold":10,
            # "scrapping_strategy":LXMLWebScrapingStrategy()
            # "stream":True,
            
            "deep_crawl_strategy":deepcrawl,
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
                            "provider": "ollama/qwen3-coder:480b-cloud",
                            "api_token": "1c5815a581be48acaed58ef87b30237f.YpZ3qB4Ny6_JLuuNILV6X1n8",
                            "base_url": "https://unsingable-streakedly-letha.ngrok-free.dev"
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
                    "instruction": "Extract any contact details in the url about the person/company like name,linkedin,email,phone number.",
                    "apply_chunking": False,
                    "input_format": "markdown"
                }
            }
        }
    }
                })
                data = response.json()
                print(len(data.get("results")))
                
                for result in data.get('results'):
                    print(result.get("extracted_content"))

                # leads_data = await crawl(url,job_details)
                # print("FINAL DATA",leads_data)


                # if leads_data:
                #     results.append(leads_data)
                #     self.db.mark_url_visited(url,job_id)
                #     count += 1

        


            except Exception as e:
                print(f"Error scraping {both_links}: {e}")
        print(f'url is {both_links} is done')

      

        return results


# async def main():
#     # stuff = await crawl("https://www.santarama-miniland.co.za/",{"job_id":1,"job_name":"test1","lead_type":"person"}) 
#     # stuff = await crawl("https://www.dninvest.co.za",{"job_id":1,"job_name":"test1","lead_type":"person"})
#     stuff = await Scraper(Database()).scrape_urls(['https://bakertillyjhb.co.za/'],1,1,{"job_name":"test1","lead_type":"person"})
#     print(stuff)

# asyncio.run(main())


