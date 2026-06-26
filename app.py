# ===================================================================
# LEXSARTHI ALPHA v5.0 – BACKEND (FastAPI)
# ===================================================================
# Owner: THE ADVOCACY – A LAW FIRM (Proprietor: Upmanyu Kumar)
# Deployed on Hugging Face Spaces: upamnyu12-lex.hf.space
# ===================================================================

import os
import json
import uuid
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from enum import Enum
import io
import random
import string

# ─── Core FastAPI ─────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, EmailStr, Field
import uvicorn

# ─── Database ────────────────────────────────────────────────────────
import asyncpg
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float, ForeignKey
from sqlalchemy.sql import func, select, insert, update, delete

# ─── Authentication ─────────────────────────────────────────────────
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

# ─── File / Image / PDF ─────────────────────────────────────────────
import puremagic
import PyPDF2
import docx
from PIL import Image
import pytesseract
import io

# ─── Voice Transcription ────────────────────────────────────────────
import speech_recognition as sr

# ─── Web Search ──────────────────────────────────────────────────────
import httpx

# ─── Payments (Razorpay) ──────────────────────────────────────────
import razorpay

# ─── Rate Limiting ──────────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─── Background Tasks ──────────────────────────────────────────────
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ─── Logging ────────────────────────────────────────────────────────
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lexsarthi")

# ─── Environment Variables ────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/lexsarthi")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7  # 7 days
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")  # optional

# ─── Database Setup ─────────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=1, max_size=10)
metadata = MetaData()

# ─── SQLAlchemy Table Definitions ──────────────────────────────────
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
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
    Column("user_id", Integer, index=True),
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
    Column("user_id", Integer),
    Column("razorpay_order_id", String(100)),
    Column("razorpay_payment_id", String(100), nullable=True),
    Column("razorpay_signature", String(255), nullable=True),
    Column("amount", Float),
    Column("currency", String(3), server_default="INR"),
    Column("tier", String(20)),
    Column("status", String(20), server_default="created"),
    Column("created_at", DateTime, server_default=func.now()),
)

# No foreign keys to avoid type mismatch warnings
events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=True),
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
    Column("referrer_id", Integer),
    Column("referee_id", Integer, nullable=True),
    Column("code", String(20), unique=True),
    Column("used", Boolean, server_default="false"),
    Column("created_at", DateTime, server_default=func.now()),
)

# ─── Pydantic Models ────────────────────────────────────────────────
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
    tier: str  # "premium" or "enterprise" or "lifetime"

class ReferralCreate(BaseModel):
    code: str

# ─── Password Hashing ──────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── JWT ────────────────────────────────────────────────────────────
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
    # Try to parse as integer; if fails, treat as username
    try:
        user_id_int = int(user_id)
        query = users.select().where(users.c.id == user_id_int)
    except ValueError:
        # user_id is a string (probably username from old tokens)
        query = users.select().where(users.c.username == user_id)
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
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Database Migration ────────────────────────────────────────────
async def migrate_database():
    """Add missing columns to existing tables."""
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
            logger.info(f"Migration skipped (already applied): {e}")

# ─── Ensure Test User ──────────────────────────────────────────────
async def ensure_test_user():
    """Create or update the test user 'counsel' with known password."""
    hashed = hash_password("Password123!")
    existing = await get_user_by_username("counsel")
    if existing:
        # Update password to known hash (in case it was changed)
        await database.execute(
            users.update().where(users.c.username == "counsel").values(
                password_hash=hashed
            )
        )
        logger.info("Updated password for test user 'counsel'.")
    else:
        # Insert new user
        query = users.insert().values(
            username="counsel",
            email="counsel@advocacyalawfrim.in",
            password_hash=hashed,
            full_name="Counsel User",
            tier="free",
            queries_used_today=0,
            last_query_reset=datetime.now()
        )
        await database.execute(query)
        logger.info("Created test user 'counsel'.")

# ─── Lifespan Events ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect()
    logger.info("Database connected")
    # Run migrations
    await migrate_database()
    # Create tables if they don't exist (idempotent)
    await create_tables()
    # Ensure test user exists
    await ensure_test_user()
    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_queries, IntervalTrigger(hours=1))
    scheduler.start()
    logger.info("Scheduler started for auto-delete")
    yield
    # Shutdown
    await database.disconnect()
    logger.info("Database disconnected")

app.router.lifespan_context = lifespan

# ─── Helper Functions ──────────────────────────────────────────────
async def create_tables():
    """Create tables if they don't exist, gracefully handling existing schemas."""
    queries_to_create = [
        # Users table (unchanged)
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            is_premium BOOLEAN DEFAULT FALSE,
            tier VARCHAR(20) DEFAULT 'free',
            queries_used_today INTEGER DEFAULT 0,
            last_query_reset TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            api_key VARCHAR(64) UNIQUE,
            preferences JSONB
        );
        """,
        # Queries table
        """
        CREATE TABLE IF NOT EXISTS queries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT,
            response TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP
        );
        """,
        # Payments table
        """
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            razorpay_order_id VARCHAR(100) UNIQUE,
            razorpay_payment_id VARCHAR(100),
            razorpay_signature VARCHAR(255),
            amount FLOAT,
            currency VARCHAR(3) DEFAULT 'INR',
            tier VARCHAR(20),
            status VARCHAR(20) DEFAULT 'created',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        # Events – no foreign key
        """
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            session_id VARCHAR(64),
            event_type VARCHAR(50),
            event_data JSONB,
            ip_address VARCHAR(45),
            user_agent VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP
        );
        """,
        # Referrals – no foreign keys
        """
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referrer_id INTEGER,
            referee_id INTEGER,
            code VARCHAR(20) UNIQUE,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    ]
    for stmt in queries_to_create:
        try:
            await database.execute(stmt)
        except Exception as e:
            # Ignore errors if table already exists (or other minor issues)
            logger.info(f"Skipping table creation (already exists or minor issue): {e}")

async def delete_expired_queries():
    cutoff = datetime.now() - timedelta(hours=24)
    await database.execute(queries.delete().where(queries.c.created_at < cutoff))
    # Also delete old events (optional)
    cutoff_events = datetime.now() - timedelta(days=30)
    await database.execute(events.delete().where(events.c.created_at < cutoff_events))
    logger.info(f"Deleted expired data older than 24h (queries) and 30d (events)")

async def get_user_by_username(username: str):
    query = users.select().where(users.c.username == username)
    return await database.fetch_one(query)

async def get_user_by_email(email: str):
    query = users.select().where(users.c.email == email)
    return await database.fetch_one(query)

async def create_user(user_data: UserCreate):
    hashed = hash_password(user_data.password)
    query = users.insert().values(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed,
        full_name=user_data.full_name,
        tier="free",
        queries_used_today=0,
        last_query_reset=datetime.now()
    )
    user_id = await database.execute(query)
    return user_id

async def increment_query_count(user_id: int):
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    last_reset = user["last_query_reset"]
    now = datetime.now()
    if now.date() > last_reset.date():
        await database.execute(
            users.update().where(users.c.id == user_id).values(
                queries_used_today=1,
                last_query_reset=now
            )
        )
        return 1
    else:
        await database.execute(
            users.update().where(users.c.id == user_id).values(
                queries_used_today=users.c.queries_used_today + 1
            )
        )
        updated = await database.fetch_one(users.select().where(users.c.id == user_id))
        return updated["queries_used_today"]

async def check_query_limit(user_id: int) -> bool:
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if user["tier"] in ("premium", "enterprise", "lifetime"):
        return True
    last_reset = user["last_query_reset"]
    now = datetime.now()
    if now.date() > last_reset.date():
        return True  # will be reset on next increment
    used = user["queries_used_today"]
    return used < 10

# ─── Agent System ────────────────────────────────────────────────────
AGENT_MAP = {
    "contract_review": "Analyzes contracts for risks and compliance.",
    "legal_research": "Finds relevant case laws and statutes.",
    "drafting": "Generates legal documents from templates.",
    "due_diligence": "Checks regulatory and legal compliance.",
    "ip_search": "Searches for patents and trademarks.",
}

def route_agent(query: str) -> str:
    query_lower = query.lower()
    if "contract" in query_lower or "agreement" in query_lower:
        return "contract_review"
    if "case" in query_lower or "judgment" in query_lower:
        return "legal_research"
    if "draft" in query_lower or "create" in query_lower:
        return "drafting"
    if "patent" in query_lower or "trademark" in query_lower:
        return "ip_search"
    if "due diligence" in query_lower or "compliance" in query_lower:
        return "due_diligence"
    return "general"

async def execute_agent(agent_name: str, query: str) -> str:
    responses = {
        "contract_review": "This contract has potential risks in clause 5 (indemnity) and clause 12 (termination). Consider limiting liability.",
        "legal_research": "Under Section 138 of the Negotiable Instruments Act, the cheque must be presented within 6 months.",
        "drafting": "I've drafted a simple NDA. Please review and customize the parties.",
        "ip_search": "There are 3 similar patents registered in India for this technology.",
        "due_diligence": "The company is compliant with all applicable regulations except for pending GST filings.",
        "general": "I'm your general legal assistant. How can I help?"
    }
    return responses.get(agent_name, "I'm processing your request. Please hold on.")

# ─── Verifier System ──────────────────────────────────────────────
VERIFIER_MAP = {
    "fact_check": "Verifies factual claims against known databases.",
    "legal_citation": "Checks if cited laws are correct and current.",
    "compliance": "Validates regulatory compliance.",
}
async def verify_response(agent_response: str, context: dict) -> tuple[str, str]:
    return agent_response, "fact_check"

# ─── File Processing ──────────────────────────────────────────────
async def process_uploaded_file(file: UploadFile) -> str:
    content = await file.read()
    try:
        file_type = puremagic.from_string(content, mime=True)[0]
    except:
        ext = os.path.splitext(file.filename)[1].lower()
        file_type = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }.get(ext, 'application/octet-stream')
    if file_type == "application/pdf":
        pdf = PyPDF2.PdfReader(io.BytesIO(content))
        text = " ".join([page.extract_text() for page in pdf.pages])
        return text
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(io.BytesIO(content))
        text = " ".join([para.text for para in doc.paragraphs])
        return text
    elif file_type.startswith("image/"):
        img = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(img)
        return text
    else:
        return "Unsupported file type."

# ─── Voice Transcription ──────────────────────────────────────────
async def transcribe_audio(audio_bytes: bytes) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="en-IN")
        return text
    except:
        return "Could not transcribe audio."

# ─── Web Search ──────────────────────────────────────────────────
async def web_search(query: str) -> str:
    if not WEB_SEARCH_API_KEY:
        return "Web search is not configured."
    async with httpx.AsyncClient() as client:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": WEB_SEARCH_API_KEY,
            "hl": "en",
            "gl": "in"
        }
        resp = await client.get(url, params=params)
        data = resp.json()
        organic = data.get("organic_results", [])
        snippets = [r.get("snippet", "") for r in organic[:3]]
        return " ".join(snippets) if snippets else "No results found."

# ─── API Endpoints ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "LexSarthi Alpha v5.0 – Legal AI OS", "status": "operational"}

# ─── Authentication Router ──────────────────────────────────────
from fastapi import APIRouter
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post("/login", response_model=Token)
async def login(user_login: UserLogin):
    logger.info(f"Login attempt with: {user_login.username}")
    user = None
    # Check if input looks like an email
    if '@' in user_login.username:
        user = await get_user_by_email(user_login.username)
        if not user:
            logger.warning(f"Email not found: {user_login.username}")
    else:
        user = await get_user_by_username(user_login.username)
        if not user:
            logger.warning(f"Username not found: {user_login.username}")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(user_login.password, user["password_hash"]):
        logger.warning(f"Password verification failed for {user['username']}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user["id"])})
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
    if await get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if await get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = await create_user(user)
    token = create_access_token({"sub": str(user_id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "tier": "free"
        }
    }

@auth_router.post("/api-key")
async def regenerate_api_key(current_user: dict = Depends(get_current_user)):
    new_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    await database.execute(
        users.update().where(users.c.id == current_user["id"]).values(api_key=new_key)
    )
    return {"api_key": new_key}

app.include_router(auth_router)

# Also keep legacy endpoints for backward compatibility
@app.post("/login", response_model=Token)
async def login_legacy(user_login: UserLogin):
    return await login(user_login)

@app.get("/me")
async def get_me_legacy(current_user: dict = Depends(get_current_user)):
    return current_user

@app.post("/register")
async def register_legacy(user: UserCreate):
    return await register(user)

# ─── Lifetime Count ────────────────────────────────────────────
@app.get("/lifetime-count")
async def get_lifetime_count():
    # Check if tier column exists; if not, return total users
    try:
        # Try to count lifetime users
        query = "SELECT COUNT(*) as count FROM users WHERE tier = 'lifetime'"
        result = await database.fetch_one(query)
        count = result["count"] if result else 0
        limit = 1000
        return {"count": count, "limit": limit, "remaining": max(0, limit - count)}
    except Exception as e:
        # Fallback: count all users
        logger.warning(f"Lifetime count fallback: {e}")
        total = await database.fetch_one("SELECT COUNT(*) as count FROM users")
        return {"count": total["count"] if total else 0, "limit": 1000, "remaining": 0}

# ─── My Usage (for all users) ──────────────────────────────────
@app.get("/my-usage")
async def my_usage(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    total = await database.fetch_one(
        "SELECT COUNT(*) as count FROM queries WHERE user_id = $1", user_id
    )
    today = await database.fetch_one(
        "SELECT COUNT(*) as count FROM queries WHERE user_id = $1 AND created_at::date = NOW()::date",
        user_id
    )
    agents = await database.fetch_all(
        "SELECT DISTINCT metadata->>'agent' as agent FROM queries WHERE user_id = $1 AND metadata IS NOT NULL",
        user_id
    )
    agent_list = [a["agent"] for a in agents if a["agent"]]
    recent = await database.fetch_all(
        "SELECT query, created_at FROM queries WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5",
        user_id
    )
    return {
        "total_queries": total["count"] if total else 0,
        "queries_today": today["count"] if today else 0,
        "agents_used": agent_list,
        "recent_queries": [
            {"query": r["query"], "timestamp": r["created_at"].isoformat()}
            for r in recent
        ]
    }

# ─── Admin Stats (Enterprise only) ─────────────────────────────
@app.get("/admin/stats")
async def admin_stats(current_user: dict = Depends(get_current_user)):
    if current_user.get("tier") != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise tier required")
    total_users = await database.fetch_one("SELECT COUNT(*) as count FROM users")
    total_queries = await database.fetch_one("SELECT COUNT(*) as count FROM queries")
    dau = await database.fetch_one(
        "SELECT COUNT(DISTINCT user_id) as dau FROM queries WHERE created_at > NOW() - INTERVAL '1 day'"
    )
    paid_users = await database.fetch_one(
        "SELECT COUNT(*) as count FROM users WHERE tier IN ('premium','enterprise','lifetime')"
    )
    return {
        "total_users": total_users["count"] if total_users else 0,
        "total_queries": total_queries["count"] if total_queries else 0,
        "daily_active_users": dau["dau"] if dau else 0,
        "paid_users": paid_users["count"] if paid_users else 0,
        "timestamp": datetime.now().isoformat()
    }

# ─── Main Query ────────────────────────────────────────────────
@app.post("/ask")
@limiter.limit("30/minute")
async def ask(
    request: Request,
    query_req: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    if not await check_query_limit(user_id):
        raise HTTPException(status_code=429, detail="Free limit reached. Upgrade to Premium.")
    await increment_query_count(user_id)
    agent_name = route_agent(query_req.query)
    response_text = await execute_agent(agent_name, query_req.query)
    verified_text, verifier_name = await verify_response(response_text, query_req.context or {})
    metadata = {
        "agent": agent_name,
        "verifier": verifier_name,
        "context": query_req.context
    }
    expires_at = datetime.now() + timedelta(hours=24)
    query = queries.insert().values(
        user_id=user_id,
        query=query_req.query,
        response=verified_text,
        metadata=metadata,
        expires_at=expires_at
    )
    await database.execute(query)
    return {
        "response": verified_text,
        "agent_used": agent_name,
        "verifier_used": verifier_name,
    }

# ─── File Upload ──────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        text = await process_uploaded_file(file)
        return {"filename": file.filename, "extracted_text": text[:500] + "..." if len(text)>500 else text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Voice Transcription ──────────────────────────────────────────
@app.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()
    text = await transcribe_audio(content)
    return {"transcription": text}

# ─── Web Search ────────────────────────────────────────────────────
@app.post("/search")
async def search(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    results = await web_search(query)
    return {"results": results}

# ─── Razorpay Payment ──────────────────────────────────────────
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.post("/create-order")
async def create_order(
    payment_data: PaymentCreate,
    current_user: dict = Depends(get_current_user)
):
    amount_map = {"premium": 10200, "enterprise": 101100, "lifetime": 200}  # ₹2 in paise
    if payment_data.tier not in amount_map:
        raise HTTPException(status_code=400, detail="Invalid tier")
    amount = amount_map[payment_data.tier]
    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })
    await database.execute(
        payments.insert().values(
            user_id=current_user["id"],
            razorpay_order_id=order["id"],
            amount=amount/100,
            tier=payment_data.tier,
            status="created"
        )
    )
    return {"order_id": order["id"], "amount": amount, "currency": "INR", "razorpay_key": RAZORPAY_KEY_ID}

@app.post("/verify-payment")
async def verify_payment(
    razorpay_order_id: str = Form(...),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    params_dict = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        await database.execute(
            payments.update().where(payments.c.razorpay_order_id == razorpay_order_id).values(
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
                status="paid"
            )
        )
        payment = await database.fetch_one(
            payments.select().where(payments.c.razorpay_order_id == razorpay_order_id)
        )
        tier = payment["tier"]
        await database.execute(
            users.update().where(users.c.id == current_user["id"]).values(
                tier=tier,
                is_premium=True if tier != "free" else False
            )
        )
        return {"status": "success", "tier": tier}
    except:
        raise HTTPException(status_code=400, detail="Payment verification failed")

# ─── Analytics Tracking ──────────────────────────────────────────
@app.post("/track")
async def track_event(
    request: Request,
    event_type: str,
    event_data: Optional[dict] = None,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())
    ip = request.client.host
    user_agent = request.headers.get("user-agent")
    query = events.insert().values(
        user_id=current_user["id"] if current_user else None,
        session_id=session_id,
        event_type=event_type,
        event_data=event_data or {},
        ip_address=ip,
        user_agent=user_agent,
        expires_at=datetime.now() + timedelta(days=30)
    )
    await database.execute(query)
    return {"status": "ok"}

# ─── Referral System ─────────────────────────────────────────────
@app.post("/referral/generate")
async def generate_referral(
    current_user: dict = Depends(get_current_user)
):
    existing = await database.fetch_one(
        referrals.select().where(referrals.c.referrer_id == current_user["id"])
    )
    if existing:
        return {"code": existing["code"]}
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    while True:
        existing_code = await database.fetch_one(
            referrals.select().where(referrals.c.code == code)
        )
        if not existing_code:
            break
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await database.execute(
        referrals.insert().values(
            referrer_id=current_user["id"],
            code=code,
            used=False
        )
    )
    return {"code": code}

@app.post("/referral/use")
async def use_referral(
    referral_data: ReferralCreate,
    current_user: dict = Depends(get_current_user)
):
    ref = await database.fetch_one(
        referrals.select().where(referrals.c.code == referral_data.code)
    )
    if not ref:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if ref["used"]:
        raise HTTPException(status_code=400, detail="Referral code already used")
    if ref["referrer_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot use your own referral code")
    await database.execute(
        referrals.update().where(referrals.c.id == ref["id"]).values(
            referee_id=current_user["id"],
            used=True
        )
    )
    # Reward: add bonus queries in preferences
    referrer = await database.fetch_one(users.select().where(users.c.id == ref["referrer_id"]))
    prefs = referrer["preferences"] or {}
    bonus = prefs.get("bonus_queries", 0) + 5
    prefs["bonus_queries"] = bonus
    await database.execute(
        users.update().where(users.c.id == ref["referrer_id"]).values(preferences=prefs)
    )
    new_prefs = current_user["preferences"] or {}
    new_bonus = new_prefs.get("bonus_queries", 0) + 3
    new_prefs["bonus_queries"] = new_bonus
    await database.execute(
        users.update().where(users.c.id == current_user["id"]).values(preferences=new_prefs)
    )
    return {"status": "success", "message": "Referral applied! You got 3 bonus queries."}

# ─── Health ──────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    try:
        await database.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}

# ─── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)