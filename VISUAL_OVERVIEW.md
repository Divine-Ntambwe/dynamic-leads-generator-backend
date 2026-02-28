# Visual Project Overview

## Before vs After

### BEFORE (Original System)
```
main.py
  │
  ├─→ Single hardcoded query
  ├─→ Fixed URL count (200)
  ├─→ No pagination tracking
  ├─→ Basic deduplication
  └─→ No progress visibility

Result: Limited, not scalable, no guarantees
```

### AFTER (Enhanced System)
```
main.py
  │
  └─→ orchestrator.py
        │
        ├─→ queryBuilder.py (75 queries)
        │     │
        │     └─→ Province × Type × Variation
        │
        ├─→ queryHarvest.py (smart pagination)
        │     │
        │     ├─→ searchApi.py (SerpAPI)
        │     ├─→ Progress tracking
        │     └─→ URL deduplication
        │
        ├─→ scrapper.py (async scraping)
        │     │
        │     └─→ extractor.py (data extraction)
        │
        └─→ database.py (triple deduplication)
              │
              ├─→ visited_urls (URL hashes)
              ├─→ schools (fingerprints)
              └─→ query_progress (state)

Result: Scalable, guaranteed unique data, resumable
```

## Data Flow Visualization

```
┌──────────────────────────────────────────────────────────────┐
│                    START: TARGET = 2000                       │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Generate 75 Queries │
              │  • Gauteng + primary │
              │  • Limpopo + high    │
              │  • Western Cape...   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  FOR EACH QUERY:     │
              └──────────┬───────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │  Check: current >= target?    │
         └───────┬───────────────────┬───┘
                 │                   │
                YES                 NO
                 │                   │
                 ▼                   ▼
         ┌───────────┐    ┌──────────────────────┐
         │   STOP    │    │  Paginate Query      │
         │  Target   │    │  start=0,10,20...90  │
         │  Reached  │    └──────────┬───────────┘
         └───────────┘               │
                                     ▼
                         ┌──────────────────────┐
                         │  Get URLs from Page  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Filter Visited URLs │
                         │  (hash lookup)       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Scrape New URLs     │
                         │  (Playwright)        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Extract Data        │
                         │  name, email, phone  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Generate Fingerprint│
                         │  (normalized hash)   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Check Duplicate?    │
                         └──────┬───────────┬───┘
                                │           │
                              YES          NO
                                │           │
                                ▼           ▼
                         ┌──────────┐  ┌──────────┐
                         │   SKIP   │  │  INSERT  │
                         └──────────┘  └─────┬────┘
                                             │
                                             ▼
                                  ┌──────────────────┐
                                  │  Update Progress │
                                  │  Save State      │
                                  └──────────────────┘
```

## Deduplication Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: URL LEVEL                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │  URL → SHA-256 Hash → visited_urls table           │     │
│  │  Prevents: Re-scraping same webpage                │     │
│  │  Example: https://school.co.za → a3f5b8c2d1e...    │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   LAYER 2: SCHOOL LEVEL                      │
│  ┌────────────────────────────────────────────────────┐     │
│  │  School Data → Normalize → SHA-256 → Fingerprint   │     │
│  │  Prevents: Duplicate schools from different URLs   │     │
│  │  Example: "ABC School" + "012..." → d7e2f1a4b...   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  LAYER 3: DATABASE LEVEL                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  UNIQUE Constraints on:                            │     │
│  │  • visited_urls.url_hash                           │     │
│  │  • schools.fingerprint                             │     │
│  │  Prevents: Any duplicate at storage level          │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Query Generation Matrix

```
┌──────────────┬─────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│              │   Gauteng   │   Limpopo    │  Mpumalanga  │ KwaZulu-Natal│ Western Cape │
├──────────────┼─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Primary      │   3 queries │   3 queries  │   3 queries  │   3 queries  │   3 queries  │
│ School       │   (15 total)│              │              │              │              │
├──────────────┼─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ High         │   3 queries │   3 queries  │   3 queries  │   3 queries  │   3 queries  │
│ School       │   (15 total)│              │              │              │              │
├──────────────┼─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Private      │   3 queries │   3 queries  │   3 queries  │   3 queries  │   3 queries  │
│ School       │   (15 total)│              │              │              │              │
├──────────────┼─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Secondary    │   3 queries │   3 queries  │   3 queries  │   3 queries  │   3 queries  │
│ School       │   (15 total)│              │              │              │              │
├──────────────┼─────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ College      │   3 queries │   3 queries  │   3 queries  │   3 queries  │   3 queries  │
│              │   (15 total)│              │              │              │              │
└──────────────┴─────────────┴──────────────┴──────────────┴──────────────┴──────────────┘

Total: 5 provinces × 5 types × 3 variations = 75 queries

Variations per combination:
1. "{type}" "{province}" contact email site:.za
2. {type} in {province} south africa contact details
3. {type} {province} phone number school website
```

## Pagination Example

```
Query: "primary school Gauteng contact email site:.za"

┌─────────────────────────────────────────────────────────────┐
│  Page 1 (start=0)  → 10 URLs → Filter → 8 new URLs          │
│  Page 2 (start=10) → 10 URLs → Filter → 7 new URLs          │
│  Page 3 (start=20) → 10 URLs → Filter → 6 new URLs          │
│  Page 4 (start=30) → 10 URLs → Filter → 5 new URLs          │
│  Page 5 (start=40) → 10 URLs → Filter → 4 new URLs          │
│  Page 6 (start=50) → 10 URLs → Filter → 3 new URLs          │
│  Page 7 (start=60) → 10 URLs → Filter → 2 new URLs          │
│  Page 8 (start=70) → 10 URLs → Filter → 1 new URL           │
│  Page 9 (start=80) → 10 URLs → Filter → 0 new URLs          │
│  Page 10 (start=90) → 8 URLs → Filter → 0 new URLs          │
└─────────────────────────────────────────────────────────────┘

Total: 98 URLs fetched → 36 new URLs (62 already visited)

After scraping 36 URLs:
• 28 schools extracted
• 22 unique (6 duplicates filtered by fingerprint)
• 22 inserted into database
```

## Progress Tracking Example

```
Time: 10:00 AM
┌──────────────────────────────────────────────────────────┐
│  Query: "primary school Gauteng..."                      │
│  Status: Processing page 4 (start=30)                    │
│  Schools: 450/2000 (22.5%)                               │
└──────────────────────────────────────────────────────────┘

[INTERRUPTION - Power outage]

Time: 11:00 AM (System restarted)
┌──────────────────────────────────────────────────────────┐
│  Checking query_progress table...                        │
│  Last position: start=40                                 │
│  Resuming from page 5                                    │
│  Schools: 450/2000 (no data lost)                        │
└──────────────────────────────────────────────────────────┘
```

## Database Schema Visual

```
┌─────────────────────────────────────────────────────────────┐
│                      visited_urls                            │
├──────────────┬──────────────────────────────────────────────┤
│ id           │ SERIAL PRIMARY KEY                           │
│ url          │ TEXT (full URL)                              │
│ url_hash     │ VARCHAR(64) UNIQUE ← SHA-256                 │
│ visited_at   │ TIMESTAMP                                    │
└──────────────┴──────────────────────────────────────────────┘
                              │
                              │ Referenced by scrapper
                              │
┌─────────────────────────────────────────────────────────────┐
│                         schools                              │
├──────────────┬──────────────────────────────────────────────┤
│ id           │ SERIAL PRIMARY KEY                           │
│ name         │ TEXT (school name)                           │
│ email        │ TEXT (contact email)                         │
│ phone        │ TEXT (contact phone)                         │
│ website      │ TEXT (school website)                        │
│ fingerprint  │ VARCHAR(64) UNIQUE ← SHA-256                 │
│ created_at   │ TIMESTAMP                                    │
└──────────────┴──────────────────────────────────────────────┘
                              │
                              │ Tracks unique schools
                              │
┌─────────────────────────────────────────────────────────────┐
│                    query_progress                            │
├──────────────┬──────────────────────────────────────────────┤
│ id           │ SERIAL PRIMARY KEY                           │
│ query        │ TEXT UNIQUE (search query)                   │
│ last_start   │ INTEGER (pagination position)                │
│ completed    │ BOOLEAN (finished flag)                      │
│ created_at   │ TIMESTAMP                                    │
│ updated_at   │ TIMESTAMP                                    │
└──────────────┴──────────────────────────────────────────────┘
```

## File Structure

```
school_scrapper_app/
│
├── Core Application
│   ├── main.py              ← Entry point
│   ├── orchestrator.py      ← Coordinator
│   ├── database.py          ← Data layer
│   ├── scrapper.py          ← Web scraping
│   ├── extractor.py         ← Data extraction
│   ├── searchApi.py         ← SerpAPI client
│   ├── queryBuilder.py      ← Query generator
│   ├── queryHarvest.py      ← Pagination handler
│   └── utils.py             ← Helpers
│
├── Configuration
│   ├── config.py            ← Settings
│   └── schema.sql           ← Database schema
│
├── Setup & Testing
│   ├── init_db.py           ← DB initialization
│   ├── test_components.py   ← Component tests
│   └── stats.py             ← Statistics viewer
│
└── Documentation
    ├── README.md            ← Overview
    ├── QUICKSTART.md        ← Getting started
    ├── ARCHITECTURE.md      ← Technical details
    ├── SUMMARY.md           ← Changes summary
    └── VISUAL_OVERVIEW.md   ← This file
```

## Key Metrics

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM CAPACITY                           │
├─────────────────────────────────────────────────────────────┤
│  Queries Generated:        75                                │
│  Max URLs per Query:       100 (SerpAPI limit)               │
│  Total Potential URLs:     7,500                             │
│  Expected Conversion:      20-30% (URLs → schools)           │
│  Expected Unique Schools:  1,500 - 2,250                     │
│  Deduplication Layers:     3 (URL, School, Database)         │
│  Resume Capability:        Yes (query-level granularity)     │
│  Parallel Processing:      No (sequential for stability)     │
│  Error Recovery:           Automatic (skip & continue)       │
└─────────────────────────────────────────────────────────────┘
```

## Success Criteria

✅ **Scalability**: Handles 75 queries automatically
✅ **Target-Based**: Stops when goal reached (e.g., 2000 schools)
✅ **Pagination**: Respects SerpAPI 100-result limit
✅ **Uniqueness**: Triple-layer deduplication guarantees no duplicates
✅ **Resumability**: Can restart from interruption point
✅ **Visibility**: Real-time progress and statistics
✅ **Reliability**: Error handling and recovery
✅ **Maintainability**: Clean, documented, modular code

## Quick Commands

```bash
# Setup (one time)
python init_db.py

# Test before running
python test_components.py

# Run scraper
python main.py

# Monitor progress (separate terminal)
python stats.py

# Check database
psql school_scrapper_db -c "SELECT COUNT(*) FROM schools;"
```

---

**System Status**: ✅ Production Ready
**Last Updated**: 2024
**Version**: 2.0 (Enhanced Multi-Query System)
