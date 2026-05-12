import os
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()  # ← this was missing

security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY")

pool = None  # assigned by main.py on startup

async def get_db():
    async with pool.acquire() as conn:
        yield conn

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")