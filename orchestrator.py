import asyncio
from database import Database
from scrapper import SchoolScraper
from queryBuilder import queryBuilder
from queryHarvest import queryHarvest

class ScraperOrchestrator:
    def __init__(self, target_schools, pool):
        self.target_schools = target_schools
        self.pool = pool

    async def run(self):
        async with self.pool.acquire() as conn:
            db = Database(conn)
            scraper = SchoolScraper(db)
            query_builder = queryBuilder()
            query_harvester = queryHarvest(db)

            queries = query_builder.generate_queries()
            print(f"Generated {len(queries)} search queries")

            current_count = await db.get_school_count()
            print(f"Current schools in database: {current_count}")

            if current_count >= self.target_schools:
                print(f"Target already met: {current_count}/{self.target_schools}")
                return

            final_count = 0

            for idx, query in enumerate(queries, 1):
                current_count = await db.get_school_count()
                if current_count >= self.target_schools:
                    print(f"\n✓ Target reached: {current_count}/{self.target_schools} schools")
                    break

                remaining = self.target_schools - current_count
                print(f"\n[{idx}/{len(queries)}] Processing query: {query}")
                print(f"Progress: {current_count}/{self.target_schools} ({remaining} remaining)")

                urls = query_harvester.harvest_query(query, max_urls_per_query=100)

                if not urls:
                    print(f"No new URLs found for query")
                    continue

                print(f"Found {len(urls)} new URLs to scrape")

                schools = await scraper.scrape_urls(urls, self.target_schools)

                if schools:
                    inserted = await db.bulk_insert_schools(schools)
                    current_count += inserted
                    final_count += inserted
                    print(f"Inserted {inserted} new schools")
                else:
                    print("No schools extracted from URLs")

            print(f"\n{'='*60}")
            print(f"Scraping completed!")
            print(f"Final count: {final_count}/{self.target_schools} schools")
            print(f"{'='*60}")