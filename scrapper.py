import asyncio
from playwright.async_api import async_playwright
from extractor import extract_school_data
from utils import hash_url

class SchoolScraper:
    def __init__(self, db):
        self.db = db

    async def scrape_urls(self, urls, target_schools):
        results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            count = 0
            for url in urls:
                if count == target_schools:
                    print("Reached target school count during scraping")
                    break
                url_hash = hash_url(url)

                # Skip already visited
                if self.db.url_exists(url_hash):
                    print(f"Skipping visited: {url}")
                    continue

                try:
                    page = await context.new_page()
                    await page.goto(url, timeout=30000)

                    html = await page.content()
                    school_data = extract_school_data(html, url)

                    if school_data:
                        results.append(school_data)
                        count += 1

                    self.db.mark_url_visited(url, url_hash)

                    await page.close()

                except Exception as e:
                    print(f"Error scraping {url}: {e}")

            await browser.close()

        return results