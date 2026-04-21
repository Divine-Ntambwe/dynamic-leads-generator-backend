import asyncio
import os
from orchestrator import ScraperOrchestrator
from dotenv import load_dotenv
from fastapi import FastAPI
load_dotenv()

app = FastAPI()
# Set your target number of schools
TARGET_SCHOOLS = 20

@app.get("/")
async def root():
    return {"message": "Welcome to the School Scraper API"}

@app.get("/scrape")
async def scrape():
    orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
    await orchestrator.run()
    return {"message": "Scraping completed!"}


# async def main():
#     orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
#     await orchestrator.run()

# if __name__ == "__main__":
#     asyncio.run(main())