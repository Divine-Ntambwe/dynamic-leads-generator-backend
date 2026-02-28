# Quick Start Guide

## First Time Setup

1. **Install Dependencies**
```bash
pip install psycopg2 playwright beautifulsoup4 requests
playwright install chromium
```

2. **Create Database**
```sql
CREATE DATABASE school_scrapper_db;
```

3. **Initialize Schema**
```bash
python init_db.py
```

## Running the Scraper

**Basic Usage:**
```bash
python main.py
```

**Check Progress:**
```sql
-- Total schools collected
SELECT COUNT(*) FROM schools;

-- Schools with email
SELECT COUNT(*) FROM schools WHERE email IS NOT NULL;

-- Schools with phone
SELECT COUNT(*) FROM schools WHERE phone IS NOT NULL;

-- Query progress
SELECT query, last_start_position, completed FROM query_progress;
```

## How Deduplication Works

### 1. URL-Level (visited_urls table)
- Hash: SHA-256 of full URL
- Prevents re-scraping same page
- Example: `https://school.co.za/contact` → `a3f5b8c...`

### 2. School-Level (schools table)
- Fingerprint: SHA-256 of normalized(name + phone + email)
- Prevents duplicate schools from different URLs
- Example: "ABC School" + "0123456789" + "info@abc.co.za" → `d7e2f1a...`

### 3. Query-Level (query_progress table)
- Tracks pagination position per query
- Marks completed queries
- Enables resume after interruption

## Pagination Details

**SerpAPI Limits:**
- Max 10 results per page
- Max 100 results per query (pages 0-90)
- Start positions: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90

**Our Implementation:**
```python
for start in range(0, 91, 10):  # 10 pages
    results = search_google(query, start)
```

## Target-Based Execution

The scraper automatically:
1. Checks current school count
2. Calculates remaining needed
3. Processes queries until target met
4. Stops when target reached

**Example Output:**
```
Generated 75 search queries
Current schools in database: 450

[1/75] Processing query: "primary school" "Gauteng" contact email site:.za
Progress: 450/2000 (1550 remaining)
Found 87 new URLs to scrape
Inserted 23 new schools

[2/75] Processing query: primary school in Gauteng south africa contact details
Progress: 473/2000 (1527 remaining)
...

✓ Target reached: 2001/2000 schools
```

## Troubleshooting

**Issue: Duplicate schools appearing**
- Check fingerprint generation in `utils.py`
- Verify UNIQUE constraint on `schools.fingerprint`

**Issue: Same URLs being scraped**
- Check `visited_urls` table
- Verify hash_url function

**Issue: Scraper stops early**
- Check SerpAPI quota
- Review error logs
- Check query_progress table

**Issue: No results from queries**
- Verify SerpAPI key is valid
- Check internet connection
- Review excluded domains list
