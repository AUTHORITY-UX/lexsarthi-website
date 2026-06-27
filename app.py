# ===================================================================
# LEXSARTHI ALPHA v5.0 – FINAL BACKEND
# ===================================================================

import os, uuid, random, string, io, logging, re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn

from databases import Database
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.sql import func, select, insert, update, delete

import jwt
from passlib.context import CryptContext
from datetime import timezone

import puremagic, PyPDF2, docx
from PIL import Image
import pytesseract
import speech_recognition as sr
import httpx
import razorpay
import groq

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lexsarthi")

# ─── Sentence‑Transformers (optional) ────────────────────────────
try:
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    _model = SentenceTransformer('all-MiniLM-L6-v2')
    _emb_available = True
    logger.info("✅ Semantic Shiva loaded.")
except ImportError:
    _emb_available = False
    logger.warning("⚠️ SentenceTransformer not installed – using keyword fallback.")

# ─── Environment ────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")

# ─── Database ──────────────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=5, max_size=20)
metadata = MetaData()

# ─── Tables ─────────────────────────────────────────────────────────
users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True),
    Column("email", String(255), unique=True, index=True),
    Column("username", String(100), unique=True),
    Column("password_hash", String(255)),
    Column("full_name", String(255)),
    Column("is_active", Boolean, server_default="true"),
    Column("is_premium", Boolean, server_default="false"),
    Column("tier", String(20), server_default="free"),
    Column("queries_used_today", Integer, server_default="0"),
    Column("last_query_reset", DateTime, server_default=func.now()),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
    Column("api_key", String(64), nullable=True, unique=True),
    Column("preferences", JSON, nullable=True),
)

queries = Table(
    "queries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String, index=True),
    Column("query", Text),
    Column("response", Text),
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)

payments = Table(
    "payments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String),
    Column("razorpay_order_id", String(100)),
    Column("razorpay_payment_id", String(100), nullable=True),
    Column("razorpay_signature", String(255), nullable=True),
    Column("amount", Float),
    Column("currency", String(3), server_default="INR"),
    Column("tier", String(20)),
    Column("status", String(20), server_default="created"),
    Column("created_at", DateTime, server_default=func.now()),
)

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", String, nullable=True),
    Column("session_id", String(64)),
    Column("event_type", String(50)),
    Column("event_data", JSON, nullable=True),
    Column("ip_address", String(45), nullable=True),
    Column("user_agent", String(255), nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime, nullable=True),
)

referrals = Table(
    "referrals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("referrer_id", String),
    Column("referee_id", String, nullable=True),
    Column("code", String(20), unique=True),
    Column("used", Boolean, server_default="false"),
    Column("created_at", DateTime, server_default=func.now()),
)

# ─── Pydantic Models ──────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class PaymentCreate(BaseModel):
    tier: str

class ReferralCreate(BaseModel):
    code: str

# ─── Password & JWT ───────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRY_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─── Security ──────────────────────────────────────────────────────
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    query = users.select().where(users.c.id == user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except:
        return None

# ─── Rate Limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="LexSarthi Alpha v5.0", version="5.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Middleware ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ──────────────────────────────────────────────────────────────────
#   220 AGENTS + SHIVA (keep your existing code)
# ──────────────────────────────────────────────────────────────────
# (your agent generation, shiva_orchestrator, PDF load, verifiers,
#  and execute_agent functions – unchanged from the final version)

# ──────────────────────────────────────────────────────────────────
#   LIFESPAN & DATABASE MIGRATIONS
# ──────────────────────────────────────────────────────────────────

async def migrate_database():
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS tier VARCHAR(20) DEFAULT 'free';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key VARCHAR(64) UNIQUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSONB;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS queries_used_today INTEGER DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_query_reset TIMESTAMP DEFAULT NOW();",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS tier VARCHAR(20);",
    ]
    for stmt in migrations:
        try:
            await database.execute(stmt)
        except Exception as e:
            logger.info(f"Migration skipped: {e}")

async def ensure_test_user():
    hashed = hash_password("Password123!")
    existing = await get_user_by_username("counsel")
    if existing:
        await database.execute(
            users.update().where(users.c.username == "counsel").values(password_hash=hashed)
        )
        logger.info("Updated password for test user 'counsel'.")
    else:
        new_id = str(uuid.uuid4())
        query = users.insert().values(
            id=new_id,
            username="counsel",
            email="counsel@advocacyalawfrim.in",
            password_hash=hashed,
            full_name="Counsel User",
            tier="free",
            queries_used_today=0,
            last_query_reset=datetime.now()
        )
        await database.execute(query)
        logger.info(f"Created test user 'counsel' with ID {new_id}.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    logger.info("Database connected")
    await migrate_database()
    await create_tables()
    await ensure_test_user()
    # load PDFs, start scheduler (as before)
    yield
    await database.disconnect()

app.router.lifespan_context = lifespan

# ─── Helper DB Functions ──────────────────────────────────────────
async def create_tables():
    # (same as previous – keep your existing)
    pass

async def get_user_by_username(username: str):
    return await database.fetch_one(users.select().where(users.c.username == username))

async def get_user_by_email(email: str):
    return await database.fetch_one(users.select().where(users.c.email == email))

# ... (other helper functions)

# ──────────────────────────────────────────────────────────────────
#   API ROUTERS – DEFINE AFTER ALL SETUP
# ──────────────────────────────────────────────────────────────────

from fastapi import APIRouter

# ✅ ROUTER DEFINED FIRST
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# ✅ NOW DECORATE USING THE ROUTER
@auth_router.post("/login", response_model=Token)
async def login(user_login: UserLogin):
    logger.info(f"Login attempt with: {user_login.username}")
    user = None
    if '@' in user_login.username:
        user = await get_user_by_email(user_login.username)
    else:
        user = await get_user_by_username(user_login.username)

    if user is None:
        logger.warning(f"User not found: {user_login.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user_login.password, user["password_hash"]):
        logger.warning(f"Password mismatch for: {user['username']}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["id"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "tier": user.get("tier", "free"),
            "is_premium": user.get("is_premium", False),
        }
    }

@auth_router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@auth_router.post("/register")
async def register(user: UserCreate):
    # (your registration logic)
    pass

@auth_router.post("/api-key")
async def regenerate_api_key(current_user: dict = Depends(get_current_user)):
    # (regenerate key)
    pass

app.include_router(auth_router)

# ─── Legacy endpoints (optional) ──────────────────────────────
@app.post("/login", response_model=Token)
async def login_legacy(user_login: UserLogin):
    return await login(user_login)

@app.get("/me")
async def get_me_legacy(current_user: dict = Depends(get_current_user)):
    return current_user

# ─── Other endpoints (ask, upload, etc.) ──────────────────────
# (keep your existing endpoints)

# ─── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)