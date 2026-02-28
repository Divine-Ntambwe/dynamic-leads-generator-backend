# Configuration for School Scraper

# Target Settings
TARGET_SCHOOLS = 2000
MAX_URLS_PER_QUERY = 100

# Database Settings
DB_CONFIG = {
    "dbname": "school_scrapper_db",
    "user": "postgres",
    "password": "Infinity",
    "host": "localhost"
}

# SerpAPI Settings
SERPAPI_KEY = "c954f755cdd0317ea32b4c1bcffd9abe4cc4fb01ecbadf3379cbf9700050a98e"

# Scraping Settings
BROWSER_HEADLESS = True
PAGE_TIMEOUT = 30000  # milliseconds

# Filtering Settings
EXCLUDED_DOMAINS = [
    "facebook.com",
    "linkedin.com", 
    "instagram.com",
    "google.com",
    "youtube.com",
    "twitter.com"
]
