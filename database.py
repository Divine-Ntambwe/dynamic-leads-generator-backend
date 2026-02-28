import psycopg2

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="school_scrapper_db",
            user="postgres",
            password="Infinity",
            host="localhost"
        )
        self.conn.autocommit = True

    def url_exists(self, url_hash):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM visited_urls WHERE url_hash=%s", (url_hash,))
        return cur.fetchone() is not None

    def mark_url_visited(self, url, url_hash):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO visited_urls (url, url_hash) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (url, url_hash)
        )

    def school_exists(self, fingerprint):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM schools WHERE fingerprint=%s", (fingerprint,))
        return cur.fetchone() is not None

    def bulk_insert_schools(self, schools):
        cur = self.conn.cursor()

        records = [
            (
                s["name"],
                s["email"],
                s["phone"],
                s["website"],
                s["fingerprint"]
            )
            for s in schools
            if not self.school_exists(s["fingerprint"])
        ]

        if records:
            cur.executemany("""
                INSERT INTO schools (name, email, phone, website, fingerprint)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO NOTHING
            """, records)
        
        return len(records)

    def get_school_count(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM schools")
        return cur.fetchone()[0]

    def get_query_progress(self, query):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT last_start_position, completed FROM query_progress WHERE query=%s",
            (query,)
        )
        result = cur.fetchone()
        return result if result else (0, False)

    def update_query_progress(self, query, start_position, completed=False):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO query_progress (query, last_start_position, completed, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (query) DO UPDATE
            SET last_start_position = EXCLUDED.last_start_position,
                completed = EXCLUDED.completed,
                updated_at = CURRENT_TIMESTAMP
        """, (query, start_position, completed))

    def mark_query_completed(self, query):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE query_progress SET completed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE query = %s
        """, (query,))