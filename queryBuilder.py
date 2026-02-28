class queryBuilder:
    PROVINCES = [
    "Gauteng", "Limpopo", "Mpumalanga",
    "KwaZulu-Natal", "Western Cape"
    ]

    TYPES = [
        "primary school",
        "high school",
        "private school",
        "secondary school",
        "college"
    ]

    def generate_queries(self):
        queries = []

        for province in self.PROVINCES:
            for t in self.TYPES:
                queries.append(f'christian {t} contact details in {province}')
                # queries.append(f'{t} in {province} south africa contact details')
                # queries.append(f'{t} {province} phone number school website')

        return queries