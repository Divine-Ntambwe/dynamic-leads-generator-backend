import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

class Database:
    DATABASE_URL = os.getenv("DATABASE_URL")

    def __init__(self, conn):
        self.conn = conn

    # --- URL tracking ---
    async def url_exists(self, url_hash):
        result = await self.conn.fetchval(
            "SELECT 1 FROM visited_urls WHERE url_hash=$1", url_hash
        )
        return result is not None

    async def mark_url_visited(self, url, url_hash):
        await self.conn.execute(
            "INSERT INTO visited_urls (url, url_hash) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            url, url_hash
        )

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