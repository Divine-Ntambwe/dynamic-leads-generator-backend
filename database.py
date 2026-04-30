import asyncpg
import ssl
import os
from dotenv import load_dotenv
import json
import psycopg

load_dotenv()

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE
class Database:
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg.connect(DATABASE_URL)

    def __init__(self, conn = conn):
        self.conn = conn

    def add_url(self, url,job_id,query):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO visited_urls (url,visited_at,job_id,scrapped,query)
            VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s)
            """,
            (url,job_id, False,query),
        )

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
                INSERT INTO leads (job_id, job_name, lead_type, email, phone, url, organization_name, job_position, notes)
    VALUES (%(job_id)s, %(job_name)s, %(lead_type)s, %(email)s, %(phone)s, %(website)s, %(organization_name)s, %(job_position)s, %(notes)s)
            """,
                leads,
            )
            self.conn.commit()

        return len(leads)

    def get_leads_count(self,job_id):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM leads WHERE job_id = %s",(job_id,))
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

    def create_job(self, query, start_position, job_details, completed=False):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO jobs (user_email, name, lead_type, status, triggered_at, updated_at, location, job_title)
            VALUES (%s, %s, %s, False,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,%s,%s)
            RETURNING id
        """,
            (
                job_details.get('email'),
                job_details.get('job_name'),
                job_details.get('lead_type'),
                job_details.get('location'),
                job_details.get('job_title')
            ),
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

    def look_for_unfinished(self):
        cur = self.conn.cursor()
        cur.execute(
            """
        SELECT * FROM query_progress 
"""
        )
        pass

    
    # --- Schools ---
    async def school_exists(self, fingerprint):
        result = await self.conn.fetchval(
            "SELECT 1 FROM schools WHERE fingerprint=$1", fingerprint
        )
        return result is not None

    async def bulk_insert_schools(self, schools):
        records = [
            (s["name"], s["email"], s["phone"], s["website"], s["fingerprint"])
            for s in schools
            if not await self.school_exists(s["fingerprint"])
        ]

        if records:
            await self.conn.executemany("""
                INSERT INTO schools (name, email, phone, website, fingerprint)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (fingerprint) DO NOTHING
            """, records)

        return len(records)

    async def get_school_count(self):
        return await self.conn.fetchval("SELECT COUNT(*) FROM schools")

    # --- Query progress ---
    async def get_query_progress(self, query):
        result = await self.conn.fetchrow(
            "SELECT last_start_position, completed FROM query_progress WHERE query=$1",
            query
        )
        return (result["last_start_position"], result["completed"]) if result else (0, False)

    async def update_query_progress(self, query, start_position, completed=False):
        await self.conn.execute("""
            INSERT INTO query_progress (query, last_start_position, completed, updated_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (query) DO UPDATE
            SET last_start_position = EXCLUDED.last_start_position,
                completed = EXCLUDED.completed,
                updated_at = CURRENT_TIMESTAMP
        """, query, start_position, completed)

    async def mark_query_completed(self, query):
        await self.conn.execute("""
            UPDATE query_progress SET completed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE query = $1
        """, query)


# --- Helper to create tables on startup ---
async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS visited_urls (
                id SERIAL PRIMARY KEY,
                url TEXT,
                url_hash TEXT UNIQUE NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                id SERIAL PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                fingerprint TEXT UNIQUE NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS query_progress (
                query TEXT PRIMARY KEY,
                last_start_position INT DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP
            )
        """)
