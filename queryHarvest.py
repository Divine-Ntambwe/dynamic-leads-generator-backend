from searchApi import SearchAPI
from database import Database


class queryHarvest:
    def __init__(self: int = None):
        self.db = Database()
        self.search_api = SearchAPI()

    def harvest_query(self, query,job_details, max_urls_per_query=100):
        #creates a job queue and the queue id becomes the job id
        job_id = self.db.create_job(query,0,job_details)
        result = ""
        new_links = []
        target_num = job_details.get('target_num',0)

        for start in range(1,target_num+1,10):
            links = self.search_api.search_google(query, start)
            
            
            if not links:
                print(f"no links found for search query:{query} job id:{job_id}")
                result = f"no links found for search query:{query} job id:{job_id}"
                self.db.mark_job_completed(job_id,"failed")
                continue

            count = 0
            for link in links:
                if count >= target_num:
                    print("Reached target school count during harvesting")
                    break
                count+=1
                from utils import hash_url
                url_hash = hash_url(link)
                exists = self.db.url_exists(job_id, query, link)
                if not exists:
                    new_links.append(link)
                    self.db.add_url(link, job_id, query)
                else:
                    print(f"{link} has already been scrapped")

            if len(new_links) >= max_urls_per_query:
                break

        if len(new_links) == 0:
            result = f"no new links found for search query:{query} job id:{job_id}"
            self.db.mark_job_completed(job_id,"failed")
        else:
            result = f"found {len(new_links)} new urls for search query:{query} job id:{job_id}"

        return {"result": result, "urls": new_links, "job_id": job_id}