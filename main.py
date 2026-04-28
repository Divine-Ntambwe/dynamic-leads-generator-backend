import asyncio
import os
from orchestrator import ScraperOrchestrator
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
load_dotenv()

app = FastAPI()
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

# 2. Add the middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Allows all headers (including Authorization)
)

class ScrapeRequest(BaseModel):
    job_name: str = None
    lead_type: str = None
    location: str = None
    industry: Optional[str] = None
    job_position: Optional[str] = None
    description: Optional[str] = None
    add_terms: Optional[str] = None
    target_nums: Optional[str] = None




@app.get("/")
async def root():
    return {"message": "Welcome to the School Scraper API"}

@app.post("/scrape")
async def scrape(formData: ScrapeRequest):
    print(formData)
    # orchestrator = ScraperOrchestrator(formData)
    # await orchestrator.run()
    return {"message": "Scraping completed!"}


# async def main():
#     orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
#     await orchestrator.run()

# if __name__ == "__main__":
#     asyncio.run(main())