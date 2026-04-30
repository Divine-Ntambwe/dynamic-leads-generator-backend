import asyncio
from database import Database
from scrapper import Scraper
from queryBuilder import queryBuilder
from queryHarvest import queryHarvest


class ScraperOrchestrator:
    def __init__(self, scrape_request, job_id: int = None):
        self.scrape_request = scrape_request.model_dump(exclude_none=True)
        self.job_id = job_id  # from the jobs table — passed in by main.py
        self.db = Database()
        self.scraper = Scraper(self.db)
        self.query_builder = queryBuilder()
        # Pass job_id into queryHarvest so it doesn't create its own
        self.query_harvester = queryHarvest(job_id=job_id)
        self.target_num = scrape_request.target_num

    async def run(self):
        print(self.scrape_request)

        queries = self.query_builder.generate_queries(self.scrape_request)
        print(f"Generated {len(queries)} search queries")

        final_count = 0

        for idx, query in enumerate(queries, 1):

            results_urls = self.query_harvester.harvest_query(query, max_urls_per_query=100)
            print(results_urls["result"])
            urls = results_urls["urls"]

            # Always use the jobs table id — queryHarvest now returns the same one
            job_id = self.job_id

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
            print("found", urls)

            details = {
                "job_name": self.scrape_request.get("job_name"),
                "lead_type": self.scrape_request.get("lead_type"),
            }
            leads = await self.scraper.scrape_urls([urls[1]], self.target_num, job_id, details)
            print("all the leads", leads)

            if leads:
                inserted = self.db.bulk_insert_leads(leads)
                current_count += len(leads)
                final_count += len(leads)
                print(f"Inserted {inserted} new leads for query: {query}")
            else:
                print(f"No leads extracted from URLs for query: {query}")

        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"Final count: {final_count}/{self.target_num} leads")
        print(f"{'='*60}")