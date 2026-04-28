import psycopg2
import os
from dotenv import load_dotenv
import json

load_dotenv()


class Database:
    DATABASE_URL = os.getenv("DATABASE_URL")

    def __init__(self):
        self.conn = psycopg2.connect(self.DATABASE_URL)
        self.conn.autocommit = True

    def add_url(self, url,job_id,query):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO visited_urls (url,visited_at,job_id,scrapped,query)
            VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s)
            """,
            (url,job_id, False,query),
        )
        self.conn.commit()

    def url_exists(self,job_id, query_str, url):
        cur = self.conn.cursor()

        sql = """
        SELECT 1 FROM visited_urls 
        WHERE job_id = %s 
            AND query = %s 
            AND url = %s
            
        LIMIT 1;
        """

        cur.execute(sql, (job_id, query_str, url))
        return cur.fetchone() is not None

    def mark_url_visited(self, url, job_id):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE visited_urls SET scrapped= %s WHERE url = %s AND job_id=%s",
            (True,url,job_id),
        )
        self.conn.commit()

    def school_exists(self, fingerprint):
        cur = self.conn.cursor() 
        cur.execute("SELECT 1 FROM schools WHERE fingerprint=%s", (fingerprint,))
        return cur.fetchone() is not None

    def bulk_insert_leads(self, leads):
        print("In DB",leads)
        cur = self.conn.cursor()
        
        if leads:
            cur.executemany(
                """
                INSERT INTO leads (job_id,job_name, lead_type,email, phone, website,organization_name,job_position,notes)
                VALUES (%s, %s, "person",%s, %s, %s,%s,%s,%s)
            """,
                leads,
            )
            self.conn.commit()

        return len(leads)

    def get_school_count(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM leads")
        return cur.fetchone()[0]

    # get the last start position and completed status of a query
    def get_query_progress(self, query):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT last_start_position, completed FROM query_progress", (query,)
        )
        result = cur.fetchone()
        print("result", result)
        return result if result else (0, False)

    def create_query_progress(self, query, start_position, userId, completed=False):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO query_progress (query, last_start_position, completed, updated_at,user_id)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP,%s)
            RETURNING id
        """,
            (query, start_position, completed, userId),
        )
        result = cur.fetchone()
        return result[0] if result else 0

    def update_query_progress(self, job_id, start_position, completed=False):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE query_progress SET last_start_position = %s, completed = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (start_position, completed, job_id),
        )
        result = cur.fetchone()
        self.conn.commit()
        return result[0] if result else 0

    def mark_query_completed(self, job_id):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE query_progress SET completed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (job_id,),
        )

    
