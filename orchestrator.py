import asyncio
from database import Database
from scrapper import Scraper
from queryBuilder import queryBuilder
from queryHarvest import queryHarvest

class ScraperOrchestrator:
    def __init__(self, scrape_request,job_id):
        self.scrape_request = scrape_request
        self.db = Database()
        self.scraper = Scraper()
        self.query_builder = queryBuilder()
        self.job_id = job_id
        self.query_harvester = queryHarvest()
        self.target_num = scrape_request.get('target_num','')

    async def run(self,rerun=False):
        print("data sent",self.scrape_request,self.target_num)
        #generate multiple queries(array form) to search by:
        if rerun == False:
            queries = self.query_builder.generate_queries(self.scrape_request)
            print(f"Generated {len(queries)} search queries")
            print(queries)
            final_count = 0
        else:
            queries = rerun["queries"]
        job_id = self.job_id
        # await asyncio.sleep(120)
        # return
        #loop through the queries, use them in SerpAPI and scrapes the urls returned by each query
        for idx, query in enumerate(queries, 1):

            # Harvest URLs from this query
            email = self.scrape_request.get('email')
            results_urls = self.query_harvester.harvest_query(query, self.scrape_request,job_id,max_urls_per_query=100) #returns urls and job id
            print(results_urls["result"])
            urls = results_urls["urls"]


            current_count = self.db.get_leads_count(job_id)
            print("current count", current_count)

            if current_count >= self.target_num:
                print(f"\n✓ Target reached: {current_count}/{self.target_num} leads")
                break

            remaining = self.target_num - current_count
            print(f"\n[{idx}/{len(queries)}] Processing query: {query}")
            print(f"Progress: {current_count}/{self.target_num} ({remaining} remaining)")

            if not urls:
                print(f"No new URLs found for query")
                continue

            print(f"Found {len(urls)} new URLs to scrape")
           
            # Scrape the URLs
            details = {"job_name":self.scrape_request.get('job_name'),"lead_type":self.scrape_request.get('lead_type')}
            
            leads = await self.scraper.scrape_urls(urls, self.target_num,job_id,details)

            if leads:
                inserted = self.db.bulk_insert_leads(leads)
                current_count += len(leads)
                final_count += len(leads)
                print(f"Inserted {inserted} new leads for query: {query}")
            else:
                print(f"No leads extracted from URLs for query:{query}")
        
        # print(f"\n{'='*60}")
        if final_count > 0:
            self.db.mark_job_completed(job_id,"complete",final_count)
            print(f"Scraping completed!")
            print(f"Final count: {final_count}/{self.target_num} leads")
        else:
            self.db.mark_job_completed(job_id,"complete",final_count)
            print(f"Scraping completed but target not reached.")
            print(f"Final count: {final_count}/{self.target_num} leads")    


# async def test():
#     await ScraperOrchestrator(2).run()

# asyncio.run(test())
