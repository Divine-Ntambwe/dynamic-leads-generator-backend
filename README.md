# School Scraper - Scalable Multi-Query System

## Features

✅ **Multi-Query Execution** - Automatically generates and executes multiple search queries
✅ **Target-Based Scraping** - Stops when desired number of schools is reached
✅ **Smart Pagination** - Handles SerpAPI's 100-result limit (10 results × 10 pages)
✅ **Dual Deduplication** - URL-level and school-level fingerprinting
✅ **Progress Tracking** - Resumes from last position if interrupted
✅ **Guaranteed Uniqueness** - Database constraints prevent duplicates

## Architecture

```
main.py → orchestrator.py → queryBuilder.py (generates queries)
                          ↓
                    queryHarvest.py (paginates & deduplicates URLs)
                          ↓
                    scrapper.py (extracts data)
                          ↓
                    database.py (stores with fingerprints)
```

## Deduplication Strategy

1. **URL Deduplication**: SHA-256 hash of URLs in `visited_urls` table
2. **School Deduplication**: Fingerprint based on name+phone+email in `schools` table
3. **Database Constraints**: UNIQUE constraints on `url_hash` and `fingerprint`
4. **Query Progress**: Tracks completed queries to avoid re-processing

## Setup

1. Initialize database:
```bash
python init_db.py
```

2. Configure target in `main.py`:
```python
TARGET_SCHOOLS = 2000  # Adjust as needed
```

3. Run scraper:
```bash
python main.py
```

## How It Works

1. **Query Generation**: Creates 75 queries (5 provinces × 5 school types × 3 variations)
2. **URL Harvesting**: For each query, paginate through up to 100 results (SerpAPI max)
3. **URL Filtering**: Skip already-visited URLs using hash lookup
4. **Data Extraction**: Scrape school name, email, phone from each URL
5. **Fingerprinting**: Generate unique fingerprint from normalized data
6. **Storage**: Insert only if fingerprint doesn't exist
7. **Progress Check**: After each query, check if target is met
8. **Resume Support**: If interrupted, resumes from last query position

## Database Schema

- `visited_urls`: Tracks scraped URLs (prevents re-scraping)
- `schools`: Stores unique schools (prevents duplicates)
- `query_progress`: Tracks query pagination state (enables resume)

## Configuration

- **SerpAPI Key**: Update in `searchApi.py`
- **Database Credentials**: Update in `database.py`
- **Target Schools**: Update `TARGET_SCHOOLS` in `main.py`
- **Query Templates**: Modify in `queryBuilder.py`
