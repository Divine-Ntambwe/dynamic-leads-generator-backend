# -------------------------------
# Search API setup (SerpAPI)
# -------------------------------
from urllib import response
import os
import requests
from dotenv import load_dotenv
from database import Database
load_dotenv()

class SearchAPI:
    def __init__(self):
        self.db = Database()


    # SERPAPI_KEY = "c954f755cdd0317ea32b4c1bcffd9abe4cc4fb01ecbadf3379cbf9700050a98e"
    
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    MAX_RESULTS_PER_PAGE = 10
    MAX_START_POSITION = 20  # SerpAPI max is 100 results (0-90 in steps of 10)
    
    #returns only one page of results
    def search_google(self, query, start=0): 
        url = "https://serpapi.com/search"
        params = {
            "q": query, #search term
            "api_key": self.SERPAPI_KEY,
            "engine": "google",
            "num": 2,
            "start": start
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            results = response.json()

            urls = []
            for result in results.get("organic_results", []):
                link = result.get("link")
                if link and not any(x in link.lower() for x in [
                     "instagram.com"
                    "google.com", "youtube.com", "twitter.com"
                ]):
                    urls.append(link)
            
            return urls
        except Exception as e:
            print(f"Search API error for query '{query}' at start={start}: {e}")
            return []