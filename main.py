import os
import sys
import asyncio
import auth
from concurrent.futures import ThreadPoolExecutor

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import ssl
import asyncpg
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, Database
from orchestrator import ScraperOrchestrator
from scrapper import Scraper


from database import Database
from auth import verify_token, get_db
from digest_router import router as digest_router
from jobs.digest_jobs import run_weekly_digests

load_dotenv()

app = FastAPI()
scheduler = AsyncIOScheduler()
executor = ThreadPoolExecutor(max_workers=5)

app.include_router(digest_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://dynamic-leads-generator-frontend-iota.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization", "Content-Type", "Accept",
        "Origin", "X-Requested-With", "Access-Control-Allow-Origin",
    ],
    expose_headers=["*"],
    max_age=3600,
)

security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment variables")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment variables")

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

pool = None


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_ctx)
    auth.pool = pool  # share pool with auth.py and digest_router
    await init_db(pool)

    scheduler.add_job(
        run_weekly_digests,
        "interval",
        minutes=1,
        args=[pool],
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()
    print("✅ Scheduler started — weekly digest cron active")


@app.on_event("shutdown")
async def shutdown():

    print("Shutting down, closing DB pool...")
    scheduler.shutdown()
    await pool.close()


# --- Auth helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(email: str) -> str:
    return jwt.encode({"sub": email}, SECRET_KEY, algorithm="HS256")



# --- Async wrapper for blocking orchestrator ---
async def run_scraper_task(orchestrator, rerun=False):
    """Run orchestrator.run() in a thread pool to avoid blocking the event loop"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, lambda: asyncio.run(orchestrator.run(rerun)))


# --- Models ---
class UserCredentials(BaseModel):
    name: str | None = None
    email: str
    password: str

class ScrapeRequest(BaseModel):
    job_name: str = None
    location: str = None
    industry: Optional[str] = None
    lead_type: str = None
    email: Optional[str] = None
    job_position: Optional[str] = None
    job_title: Optional[str] = None
    employee_range: Optional[int] = 0
    custom_keywords: Optional[str] = None
    custom_type: Optional[str] = None
    target_num: Optional[int] = 0


# --- Routes ---
@app.get("/")
async def root():
    return {"message": "Welcome to the Dynamic leads API"}


@app.post("/scrape")
async def scrape(
    formData: ScrapeRequest,
    background_tasks: BackgroundTasks = None,
    username: str = Depends(verify_token),
    conn=Depends(get_db),
):
    job_id = None  # ← define it early so except block can always reference it
    try:
        job_name = formData.job_name or "Untitled Job"
        formData = formData.model_dump(exclude_none=True)
        job_id = Database().create_job(formData)
        print("JOB ID:", job_id)

        orchestrator = ScraperOrchestrator(formData, job_id)
        # result = await orchestrator.run()
        background_tasks.add_task(run_scraper_task, orchestrator)
        

        print(f"Job {job_id} started in background")
        return {"message": "Scraping started successfully", "job_id": job_id, "status": "started"}
        # return {"message": "Scraping completed successfully", "job_id": job_id, "status": "completed", "leads_found": result}
   
    except Exception as e:
        if job_id:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE jobs SET status = $1, updated_at = NOW() WHERE id = $2",
                        "failed", job_id
                    )
            except Exception as db_error:
                print(f"Failed to update job status: {db_error}")

        print(f"Job {job_id} failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")


@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: int, username: str = Depends(verify_token), conn=Depends(get_db)):
    row = await conn.fetchrow(
        """
        SELECT id, name, status, lead_type, leads, target_leads, triggered_at, updated_at
        FROM jobs WHERE id = $1 AND user_email = $2
        """,
        job_id, username
    )
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
        
   
    # i = Scraper().get_leads_count()
    # print("COUNT:", i)
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "lead_type": row["lead_type"],
        "leads": 0,
        "target_leads": row["target_leads"],
        "triggered_at": row["triggered_at"].isoformat() if row["triggered_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "is_complete": row["status"] in ["complete", "failed"],
        "is_success": row["status"] == "complete",
    }


@app.get("/unfinished-jobs")
async def look_unfinished_jobs(username: str = Depends(verify_token), conn=Depends(get_db)):
    rows = await conn.fetch("""
        SELECT id, name, status, lead_type, leads, triggered_at, updated_at
        FROM jobs WHERE user_email = $1 AND status IN ('queued', 'running')
        ORDER BY triggered_at DESC
    """, username)
    return [dict(row) for row in rows]


@app.post("/signup")
async def signup(credentials: UserCredentials, conn=Depends(get_db)):
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", credentials.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(credentials.password)
    await conn.execute(
        "INSERT INTO users (name, email, password) VALUES ($1, $2, $3)",
        credentials.name, credentials.email, hashed,
    )
    return {"message": "User created successfully", "token": create_token(credentials.email)}


@app.post("/login")
async def login(credentials: UserCredentials, conn=Depends(get_db)):
    user = await conn.fetchrow("SELECT password FROM users WHERE email = $1", credentials.email)
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Login successful", "token": create_token(credentials.email)}


@app.get("/jobs")
async def get_jobs(username: str = Depends(verify_token), conn=Depends(get_db)):
    rows = await conn.fetch("""
        SELECT id, name, status, lead_type, leads, triggered_at, target_leads, updated_at
        FROM jobs WHERE user_email = $1 ORDER BY triggered_at DESC
    """, username)
    return [
        {
            "id":           row["id"],
            "name":         row["name"],
            "status":       row["status"],
            "lead_type":    row["lead_type"],
            "leads":        row["leads"],
            "triggered":    row["leads"],
            "target_leads": row["target_leads"],
            "updated_at":   row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


@app.get("/jobs/{job_id}/leads")
async def get_leads(job_id: int, username: str = Depends(verify_token), conn=Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM leads WHERE job_id = $1 ORDER BY created_at ASC", job_id
    )
    return [dict(row) for row in rows]


@app.patch("/leads/{lead_id}/mark")
async def mark_lead(lead_id: int, username: str = Depends(verify_token), conn=Depends(get_db)):
    row = await conn.fetchrow(
        "UPDATE leads SET marked = NOT marked WHERE id = $1 RETURNING id, marked",
        lead_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"id": row["id"], "marked": row["marked"]}


@app.post("/jobs/{job_id}/rerun")
async def rerun_job(job_id: int, background_tasks:BackgroundTasks,username: str = Depends(verify_token)):

    try:
        rerun_results = Database().re_run_job(job_id,username)
        if rerun_results and len(rerun_results) > 0:
            rerun = {
                "rerun":True,
                "queries":[rerun_results[0]]
            }
            orchestrator = ScraperOrchestrator(rerun_results[1], job_id)
            
            background_tasks.add_task(run_scraper_task, orchestrator,rerun)
            print(f"Job {job_id} started in background")
        else:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"message":"started"}
    except:
        pass
    