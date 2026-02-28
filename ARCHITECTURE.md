# System Architecture & Data Flow

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (Entry Point)                             │
│                  TARGET_SCHOOLS = 2000                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   orchestrator.py                            │
│  • Manages overall execution flow                            │
│  • Checks current count vs target                            │
│  • Iterates through queries until target met                 │
└────────┬────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────┐
         ▼                                          ▼
┌──────────────────────┐                 ┌──────────────────────┐
│  queryBuilder.py     │                 │   database.py        │
│  • Generates 75      │                 │  • PostgreSQL conn   │
│    search queries    │                 │  • Deduplication     │
│  • Province × Type   │                 │  • Progress tracking │
│  • Variations        │                 │  • Bulk inserts      │
└──────────┬───────────┘                 └──────────┬───────────┘
           │                                        │
           ▼                                        │
┌──────────────────────┐                           │
│  queryHarvest.py     │                           │
│  • Paginates query   │◄──────────────────────────┤
│  • 0→10→20...→90     │  (check visited URLs)     │
│  • Filters visited   │                           │
│  • Returns new URLs  │                           │
└──────────┬───────────┘                           │
           │                                        │
           ▼                                        │
┌──────────────────────┐                           │
│   searchApi.py       │                           │
│  • SerpAPI calls     │                           │
│  • 10 results/page   │                           │
│  • Domain filtering  │                           │
└──────────┬───────────┘                           │
           │                                        │
           ▼                                        │
┌──────────────────────┐                           │
│   scrapper.py        │                           │
│  • Playwright browser│                           │
│  • Async scraping    │                           │
│  • Error handling    │                           │
└──────────┬───────────┘                           │
           │                                        │
           ▼                                        │
┌──────────────────────┐                           │
│   extractor.py       │                           │
│  • BeautifulSoup     │                           │
│  • Regex extraction  │                           │
│  • Email & Phone     │                           │
└──────────┬───────────┘                           │
           │                                        │
           ▼                                        │
┌──────────────────────┐                           │
│     utils.py         │                           │
│  • hash_url()        │                           │
│  • fingerprint()     │                           │
│  • normalize()       │                           │
└──────────┬───────────┘                           │
           │                                        │
           └────────────────────────────────────────┤
                                                    ▼
                                    ┌───────────────────────────┐
                                    │   PostgreSQL Database     │
                                    │  • visited_urls (hashes)  │
                                    │  • schools (fingerprints) │
                                    │  • query_progress (state) │
                                    └───────────────────────────┘
```

## Execution Flow

### Phase 1: Initialization
```
1. Load TARGET_SCHOOLS from main.py
2. Connect to database
3. Generate all search queries (75 total)
4. Check current school count
```

### Phase 2: Query Processing Loop
```
FOR each query:
    IF current_count >= target:
        STOP (target reached)
    
    ELSE:
        1. Check query_progress table
        2. Resume from last_start_position
        3. Paginate: start=0,10,20...90
        4. For each page:
            - Call SerpAPI
            - Get 10 URLs
            - Filter excluded domains
            - Check if URL already visited (hash lookup)
            - Add new URLs to collection
        5. Update query_progress
```

### Phase 3: URL Scraping
```
FOR each URL batch:
    1. Launch Playwright browser
    2. FOR each URL:
        - Check visited_urls table (skip if exists)
        - Navigate to URL
        - Extract HTML
        - Parse with BeautifulSoup
        - Extract: name, email, phone
        - Generate fingerprint
        - Mark URL as visited
    3. Close browser
```

### Phase 4: Data Storage
```
FOR each school:
    1. Check if fingerprint exists in database
    2. If new:
        - Insert into schools table
        - UNIQUE constraint prevents duplicates
    3. Count inserted records
    4. Update progress
```

## Deduplication Layers

### Layer 1: URL Hash (visited_urls)
```python
url_hash = sha256(url).hexdigest()
# "https://school.co.za" → "a3f5b8c2d1e..."

if db.url_exists(url_hash):
    skip()  # Already scraped
```

### Layer 2: School Fingerprint (schools)
```python
fingerprint = sha256(
    normalize(name) + 
    normalize(phone) + 
    normalize(email)
).hexdigest()

# "abc school" + "0123456789" + "info@abc.co.za" 
# → "d7e2f1a4b3c..."

if db.school_exists(fingerprint):
    skip()  # Duplicate school
```

### Layer 3: Database Constraints
```sql
CREATE UNIQUE INDEX ON visited_urls(url_hash);
CREATE UNIQUE INDEX ON schools(fingerprint);
-- Guarantees no duplicates at DB level
```

## Pagination Strategy

### SerpAPI Limits
- Max results per query: 100
- Results per page: 10
- Pages: 10 (start positions: 0, 10, 20, ..., 90)

### Implementation
```python
for start in range(0, 91, 10):  # 0,10,20...90
    results = search_google(query, start)
    if not results:
        break  # No more results
```

### Progress Tracking
```sql
-- Save position after each page
UPDATE query_progress 
SET last_start_position = 30 
WHERE query = "primary school Gauteng";

-- Resume from saved position
SELECT last_start_position FROM query_progress
WHERE query = "primary school Gauteng";
-- Returns: 30 (continue from page 4)
```

## Target-Based Termination

```python
while True:
    current = db.get_school_count()
    
    if current >= TARGET_SCHOOLS:
        print(f"✓ Target reached: {current}/{TARGET_SCHOOLS}")
        break
    
    process_next_query()
```

## Error Handling

- **Network errors**: Logged, query continues
- **Scraping errors**: URL skipped, marked as visited
- **Database errors**: Transaction rollback
- **API quota**: Graceful degradation

## Performance Optimizations

1. **Bulk inserts**: Insert multiple schools at once
2. **Async scraping**: Playwright async API
3. **Early termination**: Stop when target met
4. **Progress caching**: Resume without re-processing
5. **Index optimization**: Hash and fingerprint indexes
