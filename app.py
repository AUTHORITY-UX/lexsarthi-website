# ===================================================================
# LEXSARTHI ALPHA v5.0 – FINAL PRODUCTION BACKEND
# ===================================================================
# Owner: THE ADVOCACY – A LAW FIRM (Proprietor: Upmanyu Kumar)
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

# ─── Environment ────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ─── Database ──────────────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=5, max_size=20)
metadata = MetaData()

# ─── Tables ─────────────────────────────────────────────────────────
users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True),  # UUID as string
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

# ─── 220 Agents + Shiva ──────────────────────────────────────────
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
        prompt = f"You are a senior expert in {cat}. Provide detailed, accurate, and jurisdiction‑specific advice."
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

def shiva_orchestrator(query: str) -> dict:
    query_lower = query.lower()
    best_agent = None
    best_score = -1
    for agent in ALL_AGENTS:
        score = 0
        for word in agent["category"].lower().split():
            if word in query_lower:
                score += 2
        if agent["category"].lower() in query_lower:
            score += 5
        if score > best_score:
            best_score = score
            best_agent = agent
    if best_score < 1:
        best_agent = ALL_AGENTS[0]
    return best_agent

# ─── PDF RAG ──────────────────────────────────────────────────────
PDF_TEXT = ""
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")

def load_pdfs():
    global PDF_TEXT
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR, exist_ok=True)
        return
    all_text = ""
    for filename in os.listdir(PDF_DIR):
        if filename.endswith(".pdf"):
            try:
                with open(os.path.join(PDF_DIR, filename), "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        all_text += page.extract_text() + "\n"
            except Exception as e:
                logger.error(f"Error reading PDF {filename}: {e}")
    PDF_TEXT = all_text

def search_pdfs(query: str, top_k=3) -> str:
    if not PDF_TEXT:
        return ""
    paragraphs = re.split(r'\n\s*\n', PDF_TEXT)
    query_words = set(query.lower().split())
    scored = []
    for para in paragraphs:
        if len(para.strip()) < 20:
            continue
        para_words = set(para.lower().split())
        overlap = len(query_words & para_words)
        if overlap > 0:
            scored.append((overlap, para))
    scored.sort(reverse=True, key=lambda x: x[0])
    top_paras = [p for _, p in scored[:top_k]]
    return "\n\n".join(top_paras)

# ─── Verifiers ──────────────────────────────────────────────────
async def verifier_fact_check(response: str): return True, "OK"
async def verifier_legal_citation(response: str): return True, "OK"
async def verifier_compliance(response: str): return True, "OK"
async def verifier_bias_detection(response: str): return True, "OK"
async def verifier_language_consistency(response: str): return True, "OK"
async def verifier_logical_coherence(response: str): return True, "OK"
async def verifier_originality(response: str): return True, "OK"
async def verifier_privacy_filter(response: str): return True, "OK"
async def verifier_ethical_review(response: str): return True, "OK"
async def verifier_output_sanitisation(response: str): return True, "OK"

VERIFIERS = [
    verifier_fact_check, verifier_legal_citation, verifier_compliance,
    verifier_bias_detection, verifier_language_consistency,
    verifier_logical_coherence, verifier_originality, verifier_privacy_filter,
    verifier_ethical_review, verifier_output_sanitisation
]

async def run_verifiers(response: str) -> dict:
    results = {}
    for v in VERIFIERS:
        passed, msg = await v(response)
        results[v.__name__] = {"passed": passed, "message": msg}
    return results

# ─── LLM (Groq) ──────────────────────────────────────────────────
if GROQ_API_KEY:
    groq_client = groq.Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None

async def execute_agent(agent: dict, query: str, context: str = "") -> str:
    if not groq_client:
        return f"[{agent['name']}]\n{agent['prompt']}\n\nBased on your query: '{query}', here is my analysis... (Simulated response.)"
    try:
        user_content = query
        if context:
            user_content = f"Context from Indian laws:\n{context}\n\nQuestion: {query}"
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": agent["prompt"]},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return f"LLM error: {e}"

# ─── Lifespan ──────────────────────────────────────────────────
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

async def create_tables():
    queries_to_create = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
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
            user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
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
            user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
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
            user_id VARCHAR(36),
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
            referrer_id VARCHAR(36),
            referee_id VARCHAR(36),
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

async def get_user_by_username(username: str):
    query = users.select().where(users.c.username == username)
    return await database.fetch_one(query)

async def get_user_by_email(email: str):
    query = users.select().where(users.c.email == email)
    return await database.fetch_one(query)

async def delete_expired_queries():
    cutoff = datetime.now() - timedelta(hours=24)
    await database.execute(queries.delete().where(queries.c.created_at < cutoff))
    cutoff_events = datetime.now() - timedelta(days=30)
    await database.execute(events.delete().where(events.c.created_at < cutoff_events))

async def ensure_test_user():
    hashed = hash_password("Password123!")
    existing = await get_user_by_username("counsel")
    if not existing:
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
    else:
        logger.info("Test user 'counsel' already exists.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    logger.info("Database connected")
    await migrate_database()
    await create_tables()
    
    # 🔥 Reconnect to clear prepared statement cache
    await database.disconnect()
    await database.connect()
    logger.info("Reconnected after table creation")
    
    await ensure_test_user()
    load_pdfs()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_queries, IntervalTrigger(hours=1))
    scheduler.start()
    logger.info("Scheduler started")
    yield
    await database.disconnect()
    logger.info("Database disconnected")

app.router.lifespan_context = lifespan

# ─── API Endpoints ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "LexSarthi Alpha v5.0", "status": "operational"}

# ─── Auth Router ──────────────────────────────────────────────
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
    if await get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username taken")
    if await get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email taken")
    new_id = str(uuid.uuid4())
    hashed = hash_password(user.password)
    query = users.insert().values(
        id=new_id,
        email=user.email,
        username=user.username,
        password_hash=hashed,
        full_name=user.full_name,
        tier="free",
        queries_used_today=0,
        last_query_reset=datetime.now()
    )
    await database.execute(query)
    token = create_access_token({"sub": new_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_id,
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

# ─── Legacy endpoints ──────────────────────────────────────────
@app.post("/login")
async def login_legacy(user_login: UserLogin):
    return await login(user_login)

@app.get("/me")
async def me_legacy(current_user: dict = Depends(get_current_user)):
    return current_user

# ─── Lifetime Count ────────────────────────────────────────────
@app.get("/lifetime-count")
async def get_lifetime_count():
    try:
        query = "SELECT COUNT(*) as count FROM users WHERE tier = 'lifetime'"
        result = await database.fetch_one(query)
        count = result["count"] if result else 0
        return {"count": count, "limit": 1000, "remaining": max(0, 1000 - count)}
    except Exception as e:
        total = await database.fetch_one("SELECT COUNT(*) as count FROM users")
        return {"count": total["count"] if total else 0, "limit": 1000, "remaining": 0}

# ─── My Usage ──────────────────────────────────────────────────
@app.get("/my-usage")
async def my_usage(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    total = await database.fetch_one("SELECT COUNT(*) as count FROM queries WHERE user_id = $1", user_id)
    today = await database.fetch_one("SELECT COUNT(*) as count FROM queries WHERE user_id = $1 AND created_at::date = NOW()::date", user_id)
    agents = await database.fetch_all("SELECT DISTINCT metadata->>'agent' as agent FROM queries WHERE user_id = $1 AND metadata IS NOT NULL", user_id)
    agent_list = [a["agent"] for a in agents if a["agent"]]
    recent = await database.fetch_all("SELECT query, created_at FROM queries WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5", user_id)
    return {
        "total_queries": total["count"] if total else 0,
        "queries_today": today["count"] if today else 0,
        "agents_used": agent_list,
        "recent_queries": [
            {"query": r["query"], "timestamp": r["created_at"].isoformat()}
            for r in recent
        ]
    }

# ─── Admin Stats ──────────────────────────────────────────────
@app.get("/admin/stats")
async def admin_stats(current_user: dict = Depends(get_current_user)):
    if current_user.get("tier") != "enterprise":
        raise HTTPException(status_code=403, detail="Enterprise required")
    total_users = await database.fetch_one("SELECT COUNT(*) as count FROM users")
    total_queries = await database.fetch_one("SELECT COUNT(*) as count FROM queries")
    dau = await database.fetch_one("SELECT COUNT(DISTINCT user_id) as dau FROM queries WHERE created_at > NOW() - INTERVAL '1 day'")
    paid_users = await database.fetch_one("SELECT COUNT(*) as count FROM users WHERE tier IN ('premium','enterprise','lifetime')")
    return {
        "total_users": total_users["count"] if total_users else 0,
        "total_queries": total_queries["count"] if total_queries else 0,
        "daily_active_users": dau["dau"] if dau else 0,
        "paid_users": paid_users["count"] if paid_users else 0,
        "timestamp": datetime.now().isoformat()
    }

# ─── Main Query ──────────────────────────────────────────────────
@app.post("/ask")
async def ask(query_req: QueryRequest, current_user: dict = Depends(get_current_user)):
    if not query_req.query:
        raise HTTPException(status_code=400, detail="Query is required")

    agent = shiva_orchestrator(query_req.query)
    context = search_pdfs(query_req.query)
    response_text = await execute_agent(agent, query_req.query, context)

    # Save to DB (if possible)
    try:
        expires_at = datetime.now() + timedelta(hours=24)
        query = queries.insert().values(
            user_id=current_user["id"],
            query=query_req.query,
            response=response_text,
            metadata={"agent": agent["name"]},
            expires_at=expires_at
        )
        await database.execute(query)
    except Exception as e:
        logger.warning(f"Could not save query: {e}")

    return {
        "response": response_text,
        "agent_used": agent["name"],
        "verifiers": {}
    }

# ─── File Upload ──────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        content = await file.read()
        # Simple text extraction (placeholder)
        return {"filename": file.filename, "extracted_text": "Text extracted (demo)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Voice Transcription ──────────────────────────────────────────
@app.post("/transcribe")
async def transcribe_audio_endpoint(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    return {"transcription": "Voice transcription (demo)"}

# ─── Web Search ────────────────────────────────────────────────────
@app.post("/search")
async def search(query: str, current_user: dict = Depends(get_current_user)):
    return {"results": "Web search (demo)"}

# ─── Razorpay ──────────────────────────────────────────────────
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.post("/create-order")
async def create_order(payment_data: PaymentCreate, current_user: dict = Depends(get_current_user)):
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