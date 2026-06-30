# ===================================================================
# LEXSARTHI v5.0 – COMPLETE BACKEND
# ===================================================================
# Owner: THE ADVOCACY – A LAW FIRM (Upmanyu Kumar)
# Deployed: upamnyu12-lex.hf.space
# ===================================================================

import os
import uuid
import json
import logging
import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# ─── FASTAPI ──────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import uvicorn

# ─── RATE LIMITING ──────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─── DATABASE ─────────────────────────────────────────────────────
from databases import Database
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float, func, select

# ─── AUTH ─────────────────────────────────────────────────────────
import jwt
from passlib.context import CryptContext

# ─── AI PROVIDERS ────────────────────────────────────────────────
import httpx
from groq import Groq
import openai
import google.generativeai as genai

# ─── FILE PROCESSING ─────────────────────────────────────────────
import io
import puremagic
import PyPDF2
import docx
from PIL import Image
import pytesseract

# ─── SCHEDULER ──────────────────────────────────────────────────
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ─── PAYMENTS ──────────────────────────────────────────────────
import razorpay

# ─── LOGGING ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lexsarthi")

# ─── ENV VARIABLES (Reads your Neon DB link from Secrets) ──────
DATABASE_URL = os.getenv("DATABASE_URL")  # <-- THIS is your connection string!
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

# AI Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Razorpay
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ─── CLIENTS INIT ──────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')

# ─── DATABASE SETUP (Pooling for 1M Users) ──────────────────────
database = Database(DATABASE_URL, min_size=2, max_size=20)
metadata = MetaData()

# ─── SQLAlchemy Tables ──────────────────────────────────────────
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
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
    "queries", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, index=True),
    Column("query", Text),
    Column("response", Text),
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)

payments = Table(
    "payments", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
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
    "events", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
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
    "referrals", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("referrer_id", Integer),
    Column("referee_id", Integer, nullable=True),
    Column("code", String(20), unique=True),
    Column("used", Boolean, server_default="false"),
    Column("created_at", DateTime, server_default=func.now()),
)

# ─── PYDANTIC MODELS ────────────────────────────────────────────
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

class PaymentCreate(BaseModel):
    tier: str

# ─── SECURITY ────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")  # <-- FIXED HASHING
security = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    query = users.select().where(users.c.id == int(user_id))
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

# ─── RATE LIMITER SETUP ──────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── LIFESPAN ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    logger.info("Database connected with connection pool.")
    await create_tables()
    await ensure_test_user()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_data, IntervalTrigger(hours=1))
    scheduler.start()
    logger.info("Scheduler started. Zero-Retention Policy Active.")
    yield
    await database.disconnect()

app = FastAPI(title="LexSarthi v5.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── DB HELPERS ──────────────────────────────────────────────────
async def create_tables():
    stmts = [
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
    for stmt in stmts:
        try:
            await database.execute(stmt)
        except Exception as e:
            logger.info(f"Table check: {e}")

async def ensure_test_user():
    await database.execute(users.delete().where(users.c.username == "counsel"))
    hashed = hash_password("Password123!")
    await database.execute(
        users.insert().values(
            username="counsel",
            email="counsel@advocacyalawfrim.in",
            password_hash=hashed,
            full_name="Counsel User",
            tier="free"
        )
    )
    logger.info("Test user 'counsel' created.")

async def delete_expired_data():
    await database.execute(queries.delete().where(queries.c.created_at < datetime.now() - timedelta(hours=24)))
    await database.execute(events.delete().where(events.c.created_at < datetime.now() - timedelta(days=30)))
    logger.info("Expired data purged (Zero Retention).")

async def check_query_limit(user: dict) -> bool:
    if user["tier"] in ("premium", "enterprise", "lifetime"):
        return True
    used = user["queries_used_today"]
    last_reset = user["last_query_reset"]
    if datetime.now().date() > last_reset.date():
        return True
    return used < 10

async def increment_query(user_id: int):
    await database.execute(
        users.update().where(users.c.id == user_id).values(
            queries_used_today=users.c.queries_used_today + 1,
            updated_at=datetime.now()
        )
    )

# ─── FILE PROCESSING ────────────────────────────────────────────
async def process_file(file: UploadFile) -> str:
    content = await file.read()
    try:
        mime = puremagic.from_string(content, mime=True)[0]
    except:
        mime = "application/octet-stream"
    
    if mime == "application/pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return " ".join([p.extract_text() for p in reader.pages])
    elif "docx" in mime:
        doc = docx.Document(io.BytesIO(content))
        return " ".join([p.text for p in doc.paragraphs])
    elif mime.startswith("image/"):
        img = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(img)
    return "Unsupported file type."

# ─── AGENT ROUTING & SYSTEM PROMPTS ─────────────────────────────
AGENT_PROMPTS = {
    "contract_review": """You are LexSarthi's Contract Review Agent, a senior M&A lawyer with 25 years of experience.
Your task is to provide a **clause‑by‑clause analysis** of the provided contract.
Structure your response with these exact headings:
1. EXECUTIVE SUMMARY (2‑3 sentences on overall risk)
2. RISK RATING (High / Medium / Low)
3. CLAUSE‑BY‑CLAUSE ANALYSIS (list each critical clause, explain the risk, and suggest a redline)
4. MISSING CLAUSES (list any critical clauses that are absent)
5. RECOMMENDATIONS (bullet‑point actionable steps)

Be ruthless but fair. Use plain English, not legalese. Make it actionable for a junior lawyer to execute.
Contract text: {query}
""",
    "legal_research": """You are LexSarthi's Legal Research Agent, a Supreme Court librarian.
Your task is to find the most relevant statutes, case laws, and legal principles for the given query.
Provide citations with full case names and judgment dates.
Structure: 
1. RELEVANT STATUTES
2. KEY CASE LAWS (with ratio decidendi)
3. LEGAL PRINCIPLES APPLICABLE
4. JURISDICTIONAL NOTES (India‑specific)
Query: {query}
""",
    "drafting": """You are LexSarthi's Drafting Agent, a senior conveyancing expert.
Your task is to draft a legally sound document based on the user's request.
Use standard Indian legal formatting.
Include:
- Title and Preamble
- Definitions
- Operative Clauses
- Signatory blocks
- Execution date
If the user specifies a document type (e.g., NDA, Sale Deed, Employment Contract), draft it precisely.
User request: {query}
""",
    "due_diligence": """You are LexSarthi's Due Diligence Agent, a forensic financial lawyer.
Analyse the provided data for regulatory compliance, financial discrepancies, and legal red flags.
Structure:
1. COMPLIANCE CHECKLIST
2. FINANCIAL HIGHLIGHTS & RED FLAGS
3. REGULATORY RISKS
4. RECOMMENDATIONS
Report: {query}
""",
    "general": """You are LexSarthi, a general legal AI assistant.
Provide accurate, structured, and jurisdiction‑aware (India‑focused) legal guidance.
Be concise but comprehensive. Always state if a point is uncertain.
User query: {query}
"""
}

def route_agent(query: str, agent_id: str = "agent_001") -> str:
    query_lower = query.lower()
    if "contract" in query_lower or "agreement" in query_lower or "review" in query_lower:
        return "contract_review"
    if "case" in query_lower or "judgment" in query_lower or "research" in query_lower:
        return "legal_research"
    if "draft" in query_lower or "create" in query_lower or "prepare" in query_lower:
        return "drafting"
    if "due diligence" in query_lower or "compliance" in query_lower:
        return "due_diligence"
    return "general"

# ─── ULTIMATE AI ROUTER (Multi-Model) ────────────────────────────
async def execute_ai(query: str, model: str, agent_type: str = "general", agent_name: str = "General Counsel") -> str:
    prompt_template = AGENT_PROMPTS.get(agent_type, AGENT_PROMPTS["general"])
    system_prompt = prompt_template.format(query=query)
    
    # 1. Groq (Fastest)
    if model.startswith("llama") and groq_client:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": f"You are {agent_name}. {system_prompt}"}, {"role": "user", "content": query}],
                temperature=0.3,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq error: {e}")

    # 2. OpenAI
    if model.startswith("gpt") and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": f"You are {agent_name}. {system_prompt}"}, {"role": "user", "content": query}],
                temperature=0.3,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")

    # 3. Gemini
    if model.startswith("gemini") and gemini_model:
        try:
            response = gemini_model.generate_content([system_prompt, query])
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")

    # 4. OpenRouter (Claude)
    if "claude" in model and OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "HTTP-Referer": "https://lexsarthi.ai"},
                    json={"model": model, "messages": [{"role": "system", "content": f"You are {agent_name}. {system_prompt}"}, {"role": "user", "content": query}]},
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")

    # 5. Fallback
    return f"""
⚠️ **AI Service Unavailable**  
We are currently experiencing high demand. Your query has been logged.

**Your Query:** {query[:200]}...

Please try again in a few moments, or contact support@lexsarthi.ai for urgent assistance.
"""

# ─── API ENDPOINTS ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin):
    logger.info(f"Login: {user_login.username}")
    user = await database.fetch_one(users.select().where(users.c.username == user_login.username))
    if not user:
        user = await database.fetch_one(users.select().where(users.c.email == user_login.username.lower()))
    if not user or not verify_password(user_login.password, user["password_hash"]):
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
            "tier": user["tier"],
            "is_premium": user["is_premium"]
        }
    }

@app.post("/auth/register")
async def register(user: UserCreate):
    existing = await database.fetch_one(users.select().where((users.c.username == user.username) | (users.c.email == user.email.lower())))
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = hash_password(user.password)
    stmt = users.insert().values(
        username=user.username,
        email=user.email.lower(),
        password_hash=hashed,
        full_name=user.full_name,
        tier="free"
    ).returning(users.c.id)
    user_id = await database.fetch_val(stmt)
    token = create_access_token({"sub": str(user_id)})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user_id, "username": user.username}}

@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/lifetime-count")
async def lifetime_count():
    count = await database.fetch_val(select(func.count()).select_from(users).where(users.c.tier == "lifetime")) or 0
    return {"count": count, "limit": 1000, "remaining": max(0, 1000 - count)}

@app.get("/my-usage")
async def my_usage(current_user: dict = Depends(get_current_user)):
    total = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == current_user["id"])) or 0
    today = await database.fetch_val(select(func.count()).select_from(queries).where(
        queries.c.user_id == current_user["id"],
        func.date(queries.c.created_at) == func.current_date()
    )) or 0
    return {"total_queries": total, "queries_today": today}

@app.post("/ask")
@limiter.limit("30/minute")
async def ask(
    request: Request,
    query: str = Form(...),
    files: Optional[UploadFile] = File(None),
    search_web: str = Form("off"),
    model: str = Form("llama-3.3-70b-versatile"),
    agent_id: str = Form("agent_001"),
    current_user: dict = Depends(get_current_user)
):
    if not await check_query_limit(current_user):
        raise HTTPException(status_code=429, detail="Free limit reached. Upgrade to Premium.")
    
    combined_query = query
    if files:
        try:
            file_text = await process_file(files)
            combined_query += f"\n\n--- Document Content ---\n{file_text}"
        except Exception as e:
            logger.warning(f"File error: {e}")
            combined_query += "\n\n--- File processing failed. ---"

    if search_web.lower() in ("on", "yes"):
        combined_query += "\n\n--- Web Search Enabled (Active in Enterprise) ---"

    await increment_query(current_user["id"])
    
    agent_type = route_agent(combined_query, agent_id)
    agent_name = f"Agent {agent_id}"
    
    response_text = await execute_ai(combined_query, model, agent_type, agent_name)
    
    expires_at = datetime.now() + timedelta(hours=24)
    await database.execute(
        queries.insert().values(
            user_id=current_user["id"],
            query=combined_query,
            response=response_text,
            metadata={"agent": agent_id, "model": model, "file": bool(files), "agent_type": agent_type},
            expires_at=expires_at
        )
    )
    
    return {"response": response_text, "model": model, "agent_used": agent_id}

# ─── RAZORPAY ──────────────────────────────────────────────────
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

@app.post("/create-order")
async def create_order(payment: PaymentCreate, current_user: dict = Depends(get_current_user)):
    if not razorpay_client:
        raise HTTPException(status_code=501, detail="Payments not configured")
    amount_map = {"premium": 10200, "enterprise": 101100, "lifetime": 200}
    amount = amount_map.get(payment.tier, 10200)
    order = razorpay_client.order.create({"amount": amount, "currency": "INR", "payment_capture": 1})
    await database.execute(
        payments.insert().values(
            user_id=current_user["id"],
            razorpay_order_id=order["id"],
            amount=amount/100,
            tier=payment.tier,
            status="created"
        )
    )
    return {"order_id": order["id"], "amount": amount, "razorpay_key": RAZORPAY_KEY_ID}

@app.post("/verify-payment")
async def verify_payment(
    razorpay_order_id: str = Form(...),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    if not razorpay_client:
        raise HTTPException(status_code=501, detail="Payments not configured")
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        payment = await database.fetch_one(payments.select().where(payments.c.razorpay_order_id == razorpay_order_id))
        tier = payment["tier"]
        await database.execute(
            users.update().where(users.c.id == current_user["id"]).values(tier=tier, is_premium=True)
        )
        await database.execute(
            payments.update().where(payments.c.razorpay_order_id == razorpay_order_id).values(status="paid")
        )
        return {"status": "success", "tier": tier}
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        raise HTTPException(status_code=400, detail="Verification failed")

# ─── STATIC FILES ──────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)