import asyncio
from orchestrator import ScraperOrchestrator

# Set your target number of schools
TARGET_SCHOOLS = 20

async def main():
    orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())