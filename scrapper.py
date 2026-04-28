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


load_dotenv()

class Leads(BaseModel):
    email: Optional[str] = None
    phone: Optional[list[str]] = None
    website: Optional[str] = None
    organization_name: Optional[str] = None
    job_position: Optional[str] = None
    notes: Optional[str] = None

extraction_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(
        provider="ollama/qwen3.5:397b-cloud",
        api_token= os.getenv("OLLAMA_API_KEY"),
        base_url="http://localhost:11434",
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
    )
    browser_config = BrowserConfig(
        headless=True 
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
        test = []
        for page_url in urls:
            result = await crawler.arun(url=page_url, config=crawl_config)

            if result.success and result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    
                    lead = {"job_id":job_details.job_id,"job_name":job_details.job_name,"lead_type":job_details.lead_type,**data[0]}

                    results.append(lead)
                    print(f"✅ Extracted: {result.extracted_content}")

                except json.JSONDecodeError:
                    print(f"⚠️  Could not parse extraction for {page_url}")
            else:
                print(f"❌ Failed: {page_url}")
        return results[0]

class Scraper:
    def __init__(self, db):
        self.db = db
        

    async def scrape_urls(self, urls, target_schools,job_id,job_details):
        results = []
        count = 0
            
        for url in urls:
            if count == target_schools:
                print("Reached target school count during scraping")
                break

            try:
                job_details = {"job_id":job_id,**job_details}
                print(job_details)
                leads_data = await crawl(url,job_details)


                if leads_data:
                    results.append(*leads_data)
                    self.db.mark_url_visited(url,job_id)
                    count += 1
                


            except Exception as e:
                print(f"Error scraping {url}: {e}")

      

        return results


# async def main():
#     # stuff = await crawl("https://www.santarama-miniland.co.za/") 
#     stuff = await crawl("https://www.example.com")
#     print(stuff)

# asyncio.run(main())

