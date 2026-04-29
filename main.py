import os
import ssl
import asyncpg
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
        "Access-Control-Allow-Origin"
    ],
    expose_headers=["*"],
    max_age=3600,
)

security = HTTPBearer()

TARGET_SCHOOLS = 20
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
async def scrape(formData: ScrapeRequest):
    print(formData)
    orchestrator = ScraperOrchestrator(formData)
    await orchestrator.run()
    return {"message": "Scraping completed!"}

@app.get("/unfinished-jobs")
async def look_unfinished_jobs():
    pass    


@app.post("/signup")
async def signup(credentials: UserCredentials, conn=Depends(get_db)):
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", credentials.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(credentials.password)
    await conn.execute(
        "INSERT INTO users (name, email, password) VALUES ($1, $2, $3)",
        credentials.name, credentials.email, hashed
    )
    return {"message": "User created successfully", "token": create_token(credentials.email)}

@app.post("/login")
async def login(credentials: UserCredentials, conn=Depends(get_db)):
    user = await conn.fetchrow("SELECT password FROM users WHERE email = $1", credentials.email)
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Login successful", "token": create_token(credentials.email)}


# async def main():
#     orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
#     await orchestrator.run()

# if __name__ == "__main__":
#     asyncio.run(main())