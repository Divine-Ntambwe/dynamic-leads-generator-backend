from searchApi import SearchAPI
from database import Database


class queryHarvest:
    def __init__(self, job_id: int = None):
        self.db = Database()
        self.search_api = SearchAPI()
        # If a job_id is provided (from the jobs table), use it.
        # Otherwise we'll create one via create_query_progress as before.
        self.provided_job_id = job_id

    def harvest_query(self, query, max_urls_per_query=100, userId=2):
        # Use the jobs table id if provided, otherwise fall back to creating one
        if self.provided_job_id is not None:
            job_id = self.provided_job_id
            # Still register the query progress row so url dedup works,
            # but use the existing job_id instead of generating a new one
            self.db.create_query_progress(query, 0, userId, job_id=job_id)
        else:
            job_id = self.db.create_query_progress(query, 0, userId)

        result = ""
        new_links = []

        for start in range(1, 2):
            links = self.search_api.search_google(query, start)

            if not links:
                print(f"no links found for search query:{query} job id:{job_id}")
                result = f"no links found for search query:{query} job id:{job_id}"
                self.db.mark_query_completed(job_id)
                break

            for link in links:
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
            self.db.mark_query_completed(job_id)
        else:
            result = f"found {len(new_links)} new urls for search query:{query} job id:{job_id}"

        return {"result": result, "urls": new_links, "job_id": job_id}