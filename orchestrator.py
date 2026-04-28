import asyncio
from database import Database
from scrapper import Scraper
from queryBuilder import queryBuilder
from queryHarvest import queryHarvest



class ScraperOrchestrator:
    def __init__(self, target_schools, pool):
        self.target_schools = target_schools
        self.db = Database()
        self.scraper = Scraper(self.db)
        self.query_builder = queryBuilder()
        self.query_harvester = queryHarvest()

    async def run(self):
        #generate multiple queries(array form) to search by:
        # queries = self.query_builder.generate_queries()
        queries=["schools in gauteng"]
        print(f"Generated {len(queries)} search queries")

        #loop through the queries, use them in SerpAPI and scrapes the urls returned by each query
        for idx, query in enumerate(queries, 1):
            current_count = self.db.get_school_count()


            #check if the target is already met and stops the loop if true
            if current_count >= self.target_schools:
                print(f"\n✓ Target reached: {current_count}/{self.target_schools} schools")
                break
            
            #print remaining leads to find
            remaining = self.target_schools - current_count
            print(f"\n[{idx}/{len(queries)}] Processing query: {query}")
            print(f"Progress: {current_count}/{self.target_schools} ({remaining} remaining)")
            
            # Harvest URLs from this query
            results_urls = self.query_harvester.harvest_query(query, max_urls_per_query=100)
            print(results_urls["result"])
            urls = results_urls["urls"]
            job_id= results_urls['job_id']
            
            if not urls:
                print(f"No new URLs found for query")
                continue
            
            print(f"Found {len(urls)} new URLs to scrape")
            
            # Scrape the URLs
            details = {"test1","business"}
            leads = await self.scraper.scrape_urls(urls, self.target_schools,job_id,details)
            print("all the leads", leads)
            final_count = 0
            if leads:
                inserted = self.db.bulk_insert_leads(leads)
                current_count += len(leads) 
                final_count += len(leads) 
                print(f"Inserted {inserted} new leads for query:{query}")
            else:
                print(f"No leads extracted from URLs for query:{query}")
        
        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"Final count: {final_count}/{self.target_schools} leads")
        print(f"{'='*60}")


async def test():
    await ScraperOrchestrator(2).run()

asyncio.run(test())
