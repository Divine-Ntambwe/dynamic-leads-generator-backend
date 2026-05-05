import os
import sys
import asyncio

# Fix for Windows asyncio subprocess issues - MUST be set before any async operations
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import ssl
import asyncpg
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
# from jose import jwt
# from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional, Dict, Set
from database import init_db
from orchestrator import ScraperOrchestrator

from database import Database

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
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, job_id: int, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        print(f"WebSocket connected for job {job_id}. Total clients: {len(self.active_connections[job_id])}")

    def disconnect(self, job_id: int, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        print(f"WebSocket disconnected for job {job_id}")

    async def broadcast(self, job_id: int, message: dict):
        if job_id in self.active_connections:
            connections = list(self.active_connections[job_id])
            print(f"Broadcasting message to {len(connections)} connections for job {job_id}")
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"WebSocket broadcast failed for job {job_id}: {e}")
        else:
            print(f"No active WebSocket connections to broadcast for job {job_id}")

manager = ConnectionManager()

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
    custom_keywords: Optional[str] = None
    target_num: Optional[int] = 0
    lead_type: str = None
    email: Optional[str] = None


# --- Routes ---
@app.get("/")
async def root():
    return {"message": "Welcome to the School Scraper API"}

@app.post("/scrape")
async def scrape(
    formData: ScrapeRequest,
    background_task: BackgroundTasks,
  
    username: str = Depends(verify_token),
    conn=Depends(get_db),
):
    try:
        # Create a job record first
        job_name = formData.job_name or "Untitled Job"
        formData = formData.model_dump(exclude_none=True)
        job_id = Database().create_job(formData)
        
        print("JOB ID:", job_id)
        
        # Add the orchestrator task to run in background
        background_task.add_task(run_orchestrator, formData, job_id)
        
        
        
        
        return {"message": "Scraping Started", "job_id": job_id, "status": "queued"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")

async def run_orchestrator(formData, job_id):
    """Run orchestrator in background and handle job status updates"""
    try:
        orchestrator = ScraperOrchestrator(formData, job_id)
        result = await orchestrator.run()
        
        # await manager.broadcast(job_id, {
        #     "status": "completed",
        #     "is_complete": True,
        #     "is_success": True,
        # })
        print(f"Job {job_id} completed successfully")
        return result
    except Exception as e:
        # Update job status to failed
        try:
            async with pool.acquire() as conn:
                job_row = await conn.fetchrow(
                    "UPDATE jobs SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING name",
                    "failed", job_id
                )
            
            # Broadcast failure status via WebSocket
            await manager.broadcast(job_id, {
                "status": "failed",
                "is_complete": True,
                "is_success": False,
                "name": job_row["name"] if job_row else "Job",
                "error": str(e),
            })
        except Exception as db_error:
            print(f"Failed to update job status: {db_error}")
        
        print(f"Job {job_id} failed with error: {str(e)}")
        raise


@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: int, username: str = Depends(verify_token), conn=Depends(get_db)):
    """Get the status of a specific job"""
    row = await conn.fetchrow(
        """
        SELECT id, name, status, lead_type, leads, target_leads, triggered_at, updated_at
        FROM jobs
        WHERE id = $1 AND user_email = $2
        """,
        job_id, username
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
        
    
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "lead_type": row["lead_type"],
        "leads": row["leads"],
        "target_leads": row["target_leads"],
        "triggered_at": row["triggered_at"].isoformat() if row["triggered_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "is_complete": row["status"] in ["completed", "failed"],
        "is_success": row["status"] == "completed",
    }


@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: int, token: str):
    """WebSocket endpoint for real-time job status updates"""
    try:
        # 2. Verify the JWT token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            username = payload["sub"]
        except jwt.PyJWTError:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # 3. Verify user owns this job with explicit type casting
        async with pool.acquire() as conn:
            # We use $1::text to tell Postgres: "Treat this input as text"
            # This solves the 'operator does not exist: text = integer' error
            job_row = await conn.fetchrow(
                "SELECT user_email FROM jobs WHERE id = $1",
                job_id
            )
            
            if not job_row:
                await websocket.close(code=4004, reason="Job not found")
                return
                
            if job_row["user_email"] != username:
                await websocket.close(code=4003, reason="Unauthorized")
                return
        
        # 4. Connect to your ConnectionManager
        await manager.connect(job_id, websocket)

        # Send current job state immediately so late-connecting clients don't miss completion
        async with pool.acquire() as conn:
            current_job = await conn.fetchrow(
                "SELECT status, name, leads, target_leads FROM jobs WHERE id = $1",
                job_id
            )
        print("finished job", current_job)
        if current_job:
            await websocket.send_json({
                "status": current_job["status"],
                "name": current_job["name"],
                "leads": current_job["leads"],
                "target_leads": current_job["target_leads"],
                "is_complete": current_job["status"] in ["complete", "failed"],
                "is_success": current_job["status"] == "complete",
            })

        try:
            while True:
                # Keep connection alive and listen for client messages
                data = await websocket.receive_text()
                # You can handle incoming client messages here if needed
        except WebSocketDisconnect:
            manager.disconnect(job_id, websocket)
            
    except Exception as e:
        # Log the error for debugging
        print(f"WebSocket error for job {job_id}: {str(e)}")
        try:
            # Use 1011 (Internal Error) or your custom 4000
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


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
        SELECT id, name, status, lead_type, leads, triggered_at,target_leads, updated_at
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
            "target_leads": row["target_leads"],
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