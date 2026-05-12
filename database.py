from multiprocessing import connection

import asyncpg
import ssl
import os
from dotenv import load_dotenv
import json
import psycopg2

load_dotenv()

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

class Database:
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)

    def __init__(self, conn = conn):
        self.conn = conn

    def add_url(self, url, job_id, query):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO visited_urls (url,visited_at,job_id,scrapped,query)
            VALUES (%s,CURRENT_TIMESTAMP,%s,%s,%s)
            RETURNING id
            """,
            (url, job_id, False, query),
        )
        result = cur.fetchone()
        if result is not None:
            url_id = result[0]
            self.conn.commit()
            cur.close()
            return url_id
        else:
            self.conn.commit()
            return 0

    def url_exists(self, user_email, query_str, url):
        cur = self.conn.cursor()
        sql = """
        SELECT job_id FROM visited_urls 
        WHERE 
            scrapped = TRUE
            AND query = %s 
            AND url = %s
        LIMIT 1;
        """
        cur.execute(sql, (query_str, url))
        result = cur.fetchone()
        if result is None:
            return False
        else:
            job_id = result[0]

        cur.execute("""
            SELECT * FROM jobs WHERE id = %s AND user_email = %s
        """, (job_id, user_email))
        self.conn.commit()
        final_result = cur.fetchone()
        return final_result is not None

    def mark_url_visited(self, url, job_id):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE visited_urls SET scrapped= %s WHERE url = %s AND job_id=%s",
            (True, url, job_id),
        )
        self.conn.commit()

    def school_exists(self, fingerprint):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM schools WHERE fingerprint=%s", (fingerprint,))
        return cur.fetchone() is not None

    def bulk_insert_leads(self, leads):
        print("Inserting leads...")
        cur = self.conn.cursor()
        required_fields = ['job_id', 'job_name', 'lead_type', 'email', 'phone', 'website', 'organization_name', 'job_position', 'notes']

        for lead in leads:
            if lead.get('organization_name') is None and lead.get('name') is not None:
                lead['organization_name'] = lead.get('name')
            for field in required_fields:
                if field not in lead:
                    lead[field] = None

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

    def get_leads_count(self, job_id):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM leads WHERE job_id = %s", (job_id,))
        return cur.fetchone()[0]

    def get_query_progress(self, query):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT last_start_position, completed FROM query_progress", (query,)
        )
        result = cur.fetchone()
        print("result", result)
        return result if result else (0, False)

    def create_job(self, job_details):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO jobs (
                user_email, name, lead_type, status,
                triggered_at, updated_at,
                location, job_title, target_leads, industry
            )
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                job_details.get('email'),
                job_details.get('job_name'),
                job_details.get('lead_type'),
                "running",
                job_details.get('location'),
                job_details.get('job_title'),
                job_details.get('target_num'),
                job_details.get('industry'),   # ← new
            ),
        )
        result = cur.fetchone()
        self.conn.commit()
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

    def mark_job_completed(self, job_id, status, final_count=0):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE jobs SET status = %s, updated_at = CURRENT_TIMESTAMP, leads = %s
            WHERE id = %s
            """,
            (status, final_count, job_id),
        )
        self.conn.commit()
        cur.close()
        return

    def look_for_unfinished(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM query_progress")
        pass

    # --- Schools ---
    async def school_exists(self, fingerprint):
        result = await self.conn.fetchval(
            "SELECT 1 FROM schools WHERE fingerprint=$1", fingerprint
        )
        return result is not None

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

Database().mark_job_completed(107, "complete", 13)