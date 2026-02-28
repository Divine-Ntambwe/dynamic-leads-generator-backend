import asyncio
from database import Database
from scrapper import SchoolScraper
from queryBuilder import queryBuilder
from queryHarvest import queryHarvest

class ScraperOrchestrator:
    def __init__(self, target_schools):
        self.target_schools = target_schools
        self.db = Database()
        self.scraper = SchoolScraper(self.db)
        self.query_builder = queryBuilder()
        self.query_harvester = queryHarvest(self.db)

    async def run(self):
        queries = self.query_builder.generate_queries()
        print(f"Generated {len(queries)} search queries")
        
        #current_count = self.db.get_school_count()
        current_count = 0
        print(f"Current schools in database: {current_count}")
        
        if current_count >= self.target_schools:
            print(f"Target already met: {current_count}/{self.target_schools}")
            return
        
        for idx, query in enumerate(queries, 1):
            #current_count = self.db.get_school_count()
            if current_count >= self.target_schools:
                print(f"\n✓ Target reached: {current_count}/{self.target_schools} schools")
                break
            
            remaining = self.target_schools - current_count
            print(f"\n[{idx}/{len(queries)}] Processing query: {query}")
            print(f"Progress: {current_count}/{self.target_schools} ({remaining} remaining)")
            
            # Harvest URLs from this query
            urls = self.query_harvester.harvest_query(query, max_urls_per_query=100)
            
            if not urls:
                print(f"No new URLs found for query")
                continue
            
            print(f"Found {len(urls)} new URLs to scrape")
            
            # Scrape the URLs
            schools = await self.scraper.scrape_urls(urls, self.target_schools)
            final_count = 0
            if schools:
                inserted = self.db.bulk_insert_schools(schools)
                current_count += len(schools)
                final_count += len(schools)
                print(f"Inserted {inserted} new schools")
            else:
                print("No schools extracted from URLs")
        
        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"Final count: {final_count}/{self.target_schools} schools")
        print(f"{'='*60}")
