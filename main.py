import os
import asyncpg
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from orchestrator import ScraperOrchestrator

load_dotenv()

app = FastAPI()
security = HTTPBearer()

TARGET_SCHOOLS = 20
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
DATABASE_URL = os.getenv("DATABASE_URL")  # Neon connection string

# --- DB setup ---
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

@app.on_event("startup")
async def startup():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    await conn.close()

# --- Auth helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(username: str) -> str:
    return jwt.encode({"sub": username}, SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --- Models ---
class UserCredentials(BaseModel):
    username: str
    password: str

# --- Routes ---
@app.get("/")
async def root():
    return {"message": "Welcome to the School Scraper API"}

@app.post("/signup")
async def signup(credentials: UserCredentials, conn=Depends(get_db)):
    existing = await conn.fetchrow("SELECT id FROM users WHERE username = $1", credentials.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(credentials.password)
    await conn.execute("INSERT INTO users (username, password) VALUES ($1, $2)", credentials.username, hashed)
    return {"message": "User created successfully", "token": create_token(credentials.username)}

@app.post("/login")
async def login(credentials: UserCredentials, conn=Depends(get_db)):
    user = await conn.fetchrow("SELECT password FROM users WHERE username = $1", credentials.username)
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful", "token": create_token(credentials.username)}

@app.get("/scrape")
async def scrape(username: str = Depends(verify_token)):
    orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
    await orchestrator.run()
    return {"message": "Scraping completed!", "triggered_by": username}

# async def main():
#     orchestrator = ScraperOrchestrator(target_schools=TARGET_SCHOOLS)
#     await orchestrator.run()

# if __name__ == "__main__":
#     asyncio.run(main())