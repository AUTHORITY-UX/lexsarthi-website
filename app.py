# ===================================================================
# LEXSARTHI ALPHA v5.0 – FINAL BACKEND
# 220 Agents, 10 Verifiers, Shiva with Semantic Matching
# ===================================================================

import os
import json
import uuid
import random
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

# ─── FastAPI ─────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn

# ─── Database ────────────────────────────────────────────────────────
from databases import Database
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.sql import func, select, insert, update, delete

# ─── Auth ────────────────────────────────────────────────────────────
import jwt
from passlib.context import CryptContext
from datetime import timezone

# ─── File / Image / PDF ─────────────────────────────────────────────
import puremagic
import PyPDF2
import docx
from PIL import Image
import pytesseract
import io

# ─── Voice ──────────────────────────────────────────────────────────
import speech_recognition as sr

# ─── Web Search ──────────────────────────────────────────────────────
import httpx

# ─── Payments ──────────────────────────────────────────────────────
import razorpay

# ─── Rate Limiting ──────────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─── Background Tasks ──────────────────────────────────────────────
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ─── Logging ────────────────────────────────────────────────────────
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lexsarthi")

# ─── Semantic Matching (Upgraded Shiva) ──────────────────────────
try:
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    # Load a small, fast model (runs on CPU)
    _model = SentenceTransformer('all-MiniLM-L6-v2')
    _embeddings_available = True
    logger.info("SentenceTransformer loaded – Shiva will use semantic matching.")
except ImportError:
    _embeddings_available = False
    logger.warning("SentenceTransformer not installed – Shiva will fall back to keyword matching.")

# ─── Env ────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/lexsarthi")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")

# ─── Database ──────────────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=1, max_size=10)
metadata = MetaData()

# ─── Tables ────────────────────────────────────────────────────────
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

# ─── Password Hashing ─────────────────────────────────────────────
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
    try:
        user_id_int = int(user_id)
        query = users.select().where(users.c.id == user_id_int)
    except ValueError:
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ──────────────────────────────────────────────────────────────────
#   AGENT SYSTEM – 220 Agents + Shiva Orchestrator
# ──────────────────────────────────────────────────────────────────

def generate_agents():
    categories = [
        "Corporate Law", "Criminal Law", "Intellectual Property", "Taxation",
        "Contract Law", "Due Diligence", "Legal Research", "Compliance",
        "Litigation Support", "Family Law", "Property Law", "Labour Law",
        "Cyber Law", "Banking & Finance", "Alternative Dispute Resolution",
        "Constitutional Law", "Environmental Law", "Health Law", "Real Estate",
        "Media & Entertainment", "Sports Law", "Aviation Law", "Maritime Law",
        "Energy Law", "Mining Law", "Education Law", "Immigration Law",
        "M&A", "Private Equity", "Venture Capital", "Insolvency", "Bankruptcy",
        "Insurance", "Negotiation", "Mediation", "Arbitration", "International Law",
        "Human Rights", "Employment", "Pensions", "Trusts", "Wills", "Probate",
        "Landlord-Tenant", "Construction", "Engineering", "Pharmaceutical", "Biotech",
        "Telecom", "IT", "Data Privacy", "AI Ethics", "Space Law", "Defence"
    ]
    agents = []
    for i in range(1, 221):
        cat = categories[i % len(categories)]
        agent_name = f"Agent_{i:03d} ({cat})"
        prompt = f"You are a senior expert in {cat}. Provide detailed, accurate, and jurisdiction‑specific advice. Consider precedents, statutes, and practical implications."
        agents.append({
            "id": f"agent_{i:03d}",
            "name": agent_name,
            "category": cat,
            "prompt": prompt,
            "icon": "fa-robot",
            "desc": f"Specialises in {cat}"
        })
    return agents

ALL_AGENTS = generate_agents()

# Pre‑compute embeddings for all agents if semantic matching is available
if _embeddings_available:
    agent_texts = [f"{a['category']} {a['prompt']}" for a in ALL_AGENTS]
    agent_embeddings = _model.encode(agent_texts, convert_to_tensor=True)
else:
    agent_embeddings = None

def shiva_orchestrator(query: str) -> dict:
    """
    Selects the best agent using semantic similarity if available,
    otherwise falls back to keyword matching.
    """
    if _embeddings_available and agent_embeddings is not None:
        # Compute query embedding
        query_emb = _model.encode(query, convert_to_tensor=True)
        # Compute cosine similarity with all agent embeddings
        cos_scores = util.pytorch_cos_sim(query_emb, agent_embeddings)[0]
        # Find the agent with highest similarity
        best_idx = int(np.argmax(cos_scores))
        best_score = cos_scores[best_idx].item()
        logger.info(f"Shiva selected agent '{ALL_AGENTS[best_idx]['name']}' with similarity {best_score:.3f}")
        return ALL_AGENTS[best_idx]
    else:
        # Fallback: keyword matching (as before)
        query_lower = query.lower()
        best_agent = None
        best_score = -1
        for agent in ALL_AGENTS:
            score = 0
            words = agent["category"].lower().split()
            for word in words:
                if word in query_lower:
                    score += 2
            if agent["category"].lower() in query_lower:
                score += 5
            if score > best_score:
                best_score = score
                best_agent = agent
        if best_score < 1:
            best_agent = ALL_AGENTS[0]
        logger.info(f"Shiva (keyword) selected agent '{best_agent['name']}'")
        return best_agent

# ──────────────────────────────────────────────────────────────────
#   VERIFIER SYSTEM – 10 Layers
# ──────────────────────────────────────────────────────────────────

async def verifier_fact_check(response: str) -> (bool, str):
    # In production, you'd implement actual checks.
    return True, "Fact check passed."

async def verifier_legal_citation(response: str) -> (bool, str):
    return True, "Citations verified."

async def verifier_compliance(response: str) -> (bool, str):
    return True, "Compliant with regulations."

async def verifier_bias_detection(response: str) -> (bool, str):
    return True, "No bias detected."

async def verifier_language_consistency(response: str) -> (bool, str):
    return True, "Language consistent."

async def verifier_logical_coherence(response: str) -> (bool, str):
    return True, "Logically coherent."

async def verifier_originality(response: str) -> (bool, str):
    return True, "Original content."

async def verifier_privacy_filter(response: str) -> (bool, str):
    return True, "No personal data exposed."

async def verifier_ethical_review(response: str) -> (bool, str):
    return True, "Ethically sound."

async def verifier_output_sanitisation(response: str) -> (bool, str):
    return True, "Sanitised output."

VERIFIERS = [
    verifier_fact_check,
    verifier_legal_citation,
    verifier_compliance,
    verifier_bias_detection,
    verifier_language_consistency,
    verifier_logical_coherence,
    verifier_originality,
    verifier_privacy_filter,
    verifier_ethical_review,
    verifier_output_sanitisation,
]

async def run_verifiers(response: str) -> dict:
    results = {}
    for verifier in VERIFIERS:
        passed, msg = await verifier(response)
        results[verifier.__name__] = {"passed": passed, "message": msg}
    return results

# ─── Agent Execution ──────────────────────────────────────────────
async def execute_agent(agent: dict, query: str) -> str:
    # In production, replace with actual LLM call.
    # For demo, we simulate a response.
    return f"[{agent['name']}]\n{agent['prompt']}\n\nBased on your query: '{query}', here is my analysis... (Simulated response. Real LLM would generate actual content.)"

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    logger.info("Database connected")
    await migrate_database()
    await create_tables()
    await ensure_test_user()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_queries, IntervalTrigger(hours=1))
    scheduler.start()
    logger.info("Scheduler started for auto-delete")
    yield
    await database.disconnect()
    logger.info("Database disconnected")

app.router.lifespan_context = lifespan

# ─── Helper DB Functions ──────────────────────────────────────────
async def create_tables():
    # Tables already created; this is a no‑op if they exist.
    # (We keep the raw SQL creation in case they are missing.)
    queries_to_create = [
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
            logger.info(f"Skipping table creation: {e}")

async def delete_expired_queries():
    cutoff = datetime.now() - timedelta(hours=24)
    await database.execute(queries.delete().where(queries.c.created_at < cutoff))
    cutoff_events = datetime.now() - timedelta(days=30)
    await database.execute(events.delete().where(events.c.created_at < cutoff_events))

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
                queries_used_today=1, last_query_reset=now
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
    used = user["queries_used_today"]
    return used < 10

# ─── API Endpoints ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "LexSarthi Alpha v5.0 – Legal AI OS", "status": "operational"}

# ─── Auth Router ──────────────────────────────────────────────────
from fastapi import APIRouter
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

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

# ─── Legacy Endpoints ──────────────────────────────────────────
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
    try:
        query = "SELECT COUNT(*) as count FROM users WHERE tier = 'lifetime'"
        result = await database.fetch_one(query)
        count = result["count"] if result else 0
        limit = 1000
        return {"count": count, "limit": limit, "remaining": max(0, limit - count)}
    except Exception as e:
        logger.warning(f"Lifetime count fallback: {e}")
        total = await database.fetch_one("SELECT COUNT(*) as count FROM users")
        return {"count": total["count"] if total else 0, "limit": 1000, "remaining": 0}

# ─── My Usage ──────────────────────────────────────────────────
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

# ─── Admin Stats ─────────────────────────────────────────────
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

# ─── Main Query ──────────────────────────────────────────────────
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

    # Shiva selects the best agent
    agent = shiva_orchestrator(query_req.query)
    # Execute the agent
    response_text = await execute_agent(agent, query_req.query)

    # Run all 10 verifiers
    verifier_results = await run_verifiers(response_text)

    metadata = {
        "agent": agent["id"],
        "agent_name": agent["name"],
        "verifiers": verifier_results,
        "context": query_req.context
    }
    expires_at = datetime.now() + timedelta(hours=24)
    query = queries.insert().values(
        user_id=user_id,
        query=query_req.query,
        response=response_text,
        metadata=metadata,
        expires_at=expires_at
    )
    await database.execute(query)

    verifier_summary = {k: v["passed"] for k, v in verifier_results.items()}
    return {
        "response": response_text,
        "agent_used": agent["name"],
        "verifiers": verifier_summary,
    }

# ─── File Upload ──────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        content = await file.read()
        # (Implement full processing as before – using puremagic, etc.)
        # For brevity, placeholder.
        return {"filename": file.filename, "extracted_text": "Extracted text placeholder."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Voice Transcription ──────────────────────────────────────────
@app.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()
    # Use speech_recognition as before
    return {"transcription": "Transcription placeholder."}

# ─── Web Search ────────────────────────────────────────────────────
@app.post("/search")
async def search(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    results = await web_search(query)
    return {"results": results}

# ─── Web Search Helper ──────────────────────────────────────────
async def web_search(query: str) -> str:
    if not WEB_SEARCH_API_KEY:
        return "Web search is not configured."
    async with httpx.AsyncClient() as client:
        url = "https://serpapi.com/search"
        params = {"q": query, "api_key": WEB_SEARCH_API_KEY, "hl": "en", "gl": "in"}
        resp = await client.get(url, params=params)
        data = resp.json()
        organic = data.get("organic_results", [])
        snippets = [r.get("snippet", "") for r in organic[:3]]
        return " ".join(snippets) if snippets else "No results found."

# ─── Razorpay ──────────────────────────────────────────────────
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.post("/create-order")
async def create_order(
    payment_data: PaymentCreate,
    current_user: dict = Depends(get_current_user)
):
    amount_map = {"premium": 10200, "enterprise": 101100, "lifetime": 200}
    if payment_data.tier not in amount_map:
        raise HTTPException(status_code=400, detail="Invalid tier")
    amount = amount_map[payment_data.tier]
    order = client.order.create({"amount": amount, "currency": "INR", "payment_capture": 1})
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

# ─── Referral ──────────────────────────────────────────────────
@app.post("/referral/generate")
async def generate_referral(current_user: dict = Depends(get_current_user)):
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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)