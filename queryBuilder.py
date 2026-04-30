class queryBuilder:

    def generate_queries(self,data):
        queries = []
          
        full_loc = data.get('location', '')
        loc = full_loc[:full_loc.find(",")]
        print(full_loc,loc)
        ind = data.get('industry', '')
        pos = data.get('job_position', '')
        title = data.get('job_title', '')
        size = data.get('employee_range')
        terms = data.get('add_terms', '')
        lead_type= data.get('lead_type','')

        # for the industry in the specific location if looking for business leads
        if lead_type == "business":
            if ind and loc and size:
                scale_term = "large" if size > 500 else "small" if size < 50 else ""
                if scale_term:
                    queries.append(f"{scale_term} {ind} companies/firms in {loc} -job -hiring")

            elif ind and loc:
                queries.append(f"{ind} companies in {loc} -job -hiring")


        if lead_type == "people":
            if title and pos and loc and ind:
                # queries.append(f'people {ind} company {title} of {pos} in {loc} contact directory -job -hiring' )
                queries.append(f'site:za.linkedin.com people {ind} company {title} of {pos} in {loc} contact directory -job -hiring' )
            elif pos and loc and ind:
                # queries.append(f'people {ind} company {pos} in {loc} contact directory -job -hiring')
                queries.append(f'site:za.linkedin.com people {ind} company {pos} in {loc} contact directory -job -hiring')

        return set(q for q in queries if q.strip())