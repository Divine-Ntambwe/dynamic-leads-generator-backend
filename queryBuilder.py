class queryBuilder:

    def generate_queries(self,data):
        print("The data",data)
        queries = []
        
        loc = data.get('location', '')
        ind = data.get('industry', '')
        pos = data.get('job_position', '')
        title = data.get('job_title', '')
        size = data.get('employee_range')
        terms = data.get('add_terms', '')


        if ind and loc:
            # queries.append(f"list of {ind} companies in {loc}")
            queries.append(f"top {ind} firms {loc}")

        # # 2. The Decision Maker Search (Title vs Position)
        # # Uses quotes to find exact staff matches
        # target_role = title or pos
        # if target_role and loc:
        #     # Example: "Head of Marketing" Johannesburg
        #     query_base = f'"{target_role}" {loc}'
        #     queries.append(query_base)
            
        #     if terms:
        #         queries.append(f"{query_base} {terms}")
        #     else:
        #         queries.append(f"{query_base} contact directory")

        # # 3. Industry + Scale (Using Employee Range)
        # # Small ranges usually imply "startup" or "boutique", large implies "enterprise"
        # if ind and loc and size:
        #     scale_term = "enterprise" if size > 500 else "small business" if size < 50 else ""
        #     if scale_term:
        #         queries.append(f"{scale_term} {ind} in {loc}")

        # # 4. The "Lead Magnet" (Industry + Location + Add Terms)
        # # Example: "Logistics companies Gauteng email address"
        # if ind and loc and terms:
        #     queries.append(f"{ind} {loc} {terms}")

        # # 5. Social/Professional Discovery
        # if ind and target_role and loc:
        #     queries.append(f"site:linkedin.com/company {ind} {loc} {target_role}")

        # Clean up and return unique results
        # Clean up: Remove empty strings and duplicates
        return set(q for q in queries if q.strip())