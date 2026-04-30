import os
import ssl
import asyncpg
import bcrypt
from jose import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
from database import init_db
from orchestrator import ScraperOrchestrator

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Allow-Origin",
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

# --- SSL for Neon ---
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# --- DB pool ---
pool = None

async def get_db():
    async with pool.acquire() as conn:
        yield conn

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_ctx)
    await init_db(pool)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

# --- Auth helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(email: str) -> str:
    return jwt.encode({"sub": email}, SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --- Models ---
class UserCredentials(BaseModel):
    name: str | None = None
    email: str
    password: str

class ScrapeRequest(BaseModel):
    job_name: str = None
    location: str = None
    industry: Optional[str] = None
    job_position: Optional[str] = None
    job_title: Optional[str] = None
    employee_range: Optional[int] = 0
    add_terms: Optional[str] = None
    target_num: Optional[int] = None
    lead_type: str = None

# --- Routes ---
@app.get("/")
async def root():
    return {"message": "Welcome to the School Scraper API"}

@app.post("/scrape")
async def scrape(
    formData: ScrapeRequest,
    username: str = Depends(verify_token),
    conn=Depends(get_db),
):
    # 1. Insert a jobs row — status starts as 'running'
    job_id = await conn.fetchval("""
        INSERT INTO jobs (user_email, name, lead_type, status)
        VALUES ($1, $2, $3, 'running')
        RETURNING id
    """, username, formData.job_name, formData.lead_type)

    try:
        # 2. Pass job_id so all leads are tagged with the correct jobs.id
        orchestrator = ScraperOrchestrator(formData, job_id=job_id)
        await orchestrator.run()

        # 3. Count inserted leads and mark job complete
        lead_count = await conn.fetchval(
            "SELECT COUNT(*) FROM leads WHERE job_id = $1", job_id
        )
        await conn.execute("""
            UPDATE jobs
            SET status = 'complete', leads = $1, updated_at = now()
            WHERE id = $2
        """, lead_count, job_id)

    except Exception as e:
        await conn.execute("""
            UPDATE jobs SET status = 'failed', updated_at = now() WHERE id = $1
        """, job_id)
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")

    return {"message": "Scraping completed!", "job_id": job_id}

@app.get("/unfinished-jobs")
async def look_unfinished_jobs(username: str = Depends(verify_token), conn=Depends(get_db)):
    rows = await conn.fetch("""
        SELECT id, name, status, lead_type, leads, triggered_at, updated_at
        FROM jobs
        WHERE user_email = $1 AND status IN ('queued', 'running')
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
        SELECT id, name, status, lead_type, leads, triggered_at, updated_at
        FROM jobs
        WHERE user_email = $1
        ORDER BY triggered_at DESC
    """, username)
    return [
        {
            "id":         row["id"],
            "name":       row["name"],
            "status":     row["status"],
            "lead_type":  row["lead_type"],
            "leads":      row["leads"],
            "triggered":  row["leads"],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
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