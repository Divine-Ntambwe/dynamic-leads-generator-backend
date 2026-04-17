from searchApi import SearchAPI
##checks for unfinished jobs 

class queryHarvest:
    def __init__(self, db):
        self.db = db
        self.search_api = SearchAPI()

    def harvest_query(self, query, max_urls_per_query=100):
        collected = []
        last_start, completed = self.db.get_query_progress(query)
        
        if completed:
            print(f"Query already completed: {query}")
            return collected

        for start in range(last_start, SearchAPI.MAX_START_POSITION + 1, SearchAPI.MAX_RESULTS_PER_PAGE):
            links = self.search_api.search_google(query, start)

            if not links:
                self.db.mark_query_completed(query)
                break
            
            # Filter out already visited URLs
            new_links = []
            for link in links:
                from utils import hash_url
                if not self.db.url_exists(hash_url(link)):
                    new_links.append(link)
            
            collected.extend(new_links)
            self.db.update_query_progress(query, start + SearchAPI.MAX_RESULTS_PER_PAGE)
            
            if len(collected) >= max_urls_per_query:
                break

        return collected