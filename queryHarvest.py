from searchApi import SearchAPI
from database import Database
#gets 

class queryHarvest:
    def __init__(self):
        self.db = Database()
        self.search_api = SearchAPI()

    def harvest_query(self, query, max_urls_per_query=100,userId=2):
        #creates a job queue and the queue id becomes the job id
        job_id = self.db.create_query_progress(query,0,userId)
        result = ""
        new_links = []
        #runs from 1 to 100 in steps of 10
        for start in range(1,2):
            #start indicates from the returned results where it should start e.g) 21 for results from page 3
 
            #getting search query results:
            # links = self.search_api.search_google(query, start)
            # links = ["https://www.santarama-miniland.co.za/","https://www.jbfa.co.za/"]
            links = ["https://www.example.com"]
            
            if not links:
                print(f"no links found for search query:{query} job id:{job_id}")
                result = f"no links found for search query:{query} job id:{job_id}"
                self.db.mark_query_completed(job_id)  
                break
            
            
            # Filter out already visited URLs
            
            for link in links:
                from utils import hash_url
                url_hash = hash_url(link)
                exists = self.db.url_exists(job_id,query,link)
                if not exists:
                    new_links.append(link)
                    self.db.add_url(link,job_id,query)
                else:
                    print(f"{link} has already been scrapped")
            if len(new_links) >= max_urls_per_query:
                break

        if len(new_links) == 0:
            result = f"no new links found for search query:{query} job id:{job_id}"
            self.db.mark_query_completed(job_id)    

        else:
            result = f"found {len(new_links)} new urls for search query:{query} job id:{job_id}"
        return {"result":result, "urls":new_links,"job_id":job_id}        


print(queryHarvest().harvest_query("schools in gauteng"))