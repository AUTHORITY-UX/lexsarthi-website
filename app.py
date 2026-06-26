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

# ─── Core FastAPI ─────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import uvicorn

# ─── Database ────────────────────────────────────────────────────────
import asyncpg
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.sql import func, select, insert, update, delete

# ─── Authentication ─────────────────────────────────────────────────
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

# ─── File / Image / PDF ─────────────────────────────────────────────
import magic
import PyPDF2
import docx
from PIL import Image
import pytesseract
import io

# ─── Voice Transcription ────────────────────────────────────────────
import speech_recognition as sr

# ─── Web Search ──────────────────────────────────────────────────────
import httpx
from bs4 import BeautifulSoup

# ─── Payments (Razorpay) ──────────────────────────────────────────
import razorpay

# ─── Agents & Verifiers ─────────────────────────────────────────────
# (We'll simulate them with a dictionary – you can replace with your actual AI logic)
from typing import Callable, Awaitable

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
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")  # e.g., SerpAPI

# ─── Database Setup ─────────────────────────────────────────────────
database = Database(DATABASE_URL)
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
    Column("tier", String(20), server_default="free"),  # free, premium, enterprise, lifetime
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
    # model_used removed to fix the error – we'll log it in metadata if needed
    Column("metadata", JSON, nullable=True),  # store extra info like agent_id, verifier_id
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),  # for 24h auto-delete
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
    Column("status", String(20), server_default="created"),  # created, paid, failed
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
    context: Optional[Dict[str, Any]] = None  # optional metadata

class QueryResponse(BaseModel):
    response: str
    agent_used: Optional[str] = None
    verifier_used: Optional[str] = None

class PaymentCreate(BaseModel):
    tier: str  # "premium" or "enterprise"

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
    # Fetch user from DB
    query = users.select().where(users.c.id == int(user_id))
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

# ─── Rate Limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="LexSarthi Alpha v5.0", version="5.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Lifespan Events ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect()
    logger.info("Database connected")
    # Create tables if not exist (optional)
    # await create_tables()
    # Start background scheduler for auto-delete
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
    """Create tables if they don't exist (for first run)"""
    # Using raw SQL for simplicity
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
        """
    ]
    for stmt in queries_to_create:
        await database.execute(stmt)

async def delete_expired_queries():
    """Delete queries older than 24 hours (zero retention)"""
    cutoff = datetime.now() - timedelta(hours=24)
    await database.execute(queries.delete().where(queries.c.created_at < cutoff))
    logger.info(f"Deleted expired queries older than {cutoff}")

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
    """Increment daily query count and reset if needed"""
    # Get user's last reset
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    last_reset = user["last_query_reset"]
    now = datetime.now()
    if now.date() > last_reset.date():
        # Reset count
        await database.execute(
            users.update().where(users.c.id == user_id).values(
                queries_used_today=1,
                last_query_reset=now
            )
        )
        return 1
    else:
        # Increment
        await database.execute(
            users.update().where(users.c.id == user_id).values(
                queries_used_today=users.c.queries_used_today + 1
            )
        )
        # return current count after increment
        updated = await database.fetch_one(users.select().where(users.c.id == user_id))
        return updated["queries_used_today"]

async def check_query_limit(user_id: int) -> bool:
    """Return True if user can make a query, else False"""
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if user["tier"] in ("premium", "enterprise", "lifetime"):
        return True
    # Free tier: 10 queries per day
    # Reset check
    last_reset = user["last_query_reset"]
    now = datetime.now()
    if now.date() > last_reset.date():
        # Reset automatically in increment_query_count
        pass
    used = user["queries_used_today"]
    return used < 10

# ─── Agent System (220 specialized agents) ────────────────────────
# In real implementation, this would call your LLM or specialized services.
# For demonstration, we return static responses.
AGENT_MAP = {
    "contract_review": "Analyzes contracts for risks and compliance.",
    "legal_research": "Finds relevant case laws and statutes.",
    "drafting": "Generates legal documents from templates.",
    "due_diligence": "Checks regulatory and legal compliance.",
    "ip_search": "Searches for patents and trademarks.",
    # ... add 215 more agents
}
# For simplicity, we'll use a default agent that routes based on keywords.
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
    """Simulate agent execution. Replace with actual AI calls."""
    # For demo, we return a canned response.
    responses = {
        "contract_review": "This contract has potential risks in clause 5 (indemnity) and clause 12 (termination). Consider limiting liability.",
        "legal_research": "Under Section 138 of the Negotiable Instruments Act, the cheque must be presented within 6 months.",
        "drafting": "I've drafted a simple NDA. Please review and customize the parties.",
        "ip_search": "There are 3 similar patents registered in India for this technology.",
        "due_diligence": "The company is compliant with all applicable regulations except for pending GST filings.",
        "general": "I'm your general legal assistant. How can I help?"
    }
    return responses.get(agent_name, "I'm processing your request. Please hold on.")

# ─── Verifier System (10 verifiers) ──────────────────────────────
VERIFIER_MAP = {
    "fact_check": "Verifies factual claims against known databases.",
    "legal_citation": "Checks if cited laws are correct and current.",
    "compliance": "Validates regulatory compliance.",
    # ... more
}
async def verify_response(agent_response: str, context: dict) -> tuple[str, str]:
    """Run the response through 10 verifiers and return verified response."""
    # Simulate verification
    return agent_response, "fact_check"

# ─── File Processing ──────────────────────────────────────────────
async def process_uploaded_file(file: UploadFile) -> str:
    """Extract text from PDF, DOCX, or image (OCR)."""
    content = await file.read()
    file_type = magic.from_buffer(content, mime=True)
    
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
    """Transcribe speech using Google Speech Recognition (or better)."""
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
    """Perform a web search and return summarized results."""
    if not WEB_SEARCH_API_KEY:
        return "Web search is not configured."
    # Example using SerpAPI
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
        # Extract organic results snippets
        organic = data.get("organic_results", [])
        snippets = [r.get("snippet", "") for r in organic[:3]]
        return " ".join(snippets) if snippets else "No results found."

# ─── API Endpoints ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "LexSarthi Alpha v5.0 – Legal AI OS", "status": "operational"}

@app.post("/register", response_model=Token)
async def register(user: UserCreate):
    # Check if user exists
    if await get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if await get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = await create_user(user)
    # Generate JWT
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

@app.post("/login", response_model=Token)
async def login(user_login: UserLogin):
    user = await get_user_by_username(user_login.username)
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
            "is_premium": user["is_premium"],
        }
    }

@app.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.post("/ask")
@limiter.limit("30/minute")  # protect against abuse
async def ask(
    request: Request,
    query_req: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Main endpoint for querying the AI."""
    user_id = current_user["id"]
    
    # Check query limit
    if not await check_query_limit(user_id):
        raise HTTPException(status_code=429, detail="Free limit reached. Upgrade to Premium.")
    
    # Increment query count
    await increment_query_count(user_id)
    
    # Route to appropriate agent
    agent_name = route_agent(query_req.query)
    agent_description = AGENT_MAP.get(agent_name, "General assistant")
    
    # Execute agent (replace with actual LLM call)
    response_text = await execute_agent(agent_name, query_req.query)
    
    # Run verifiers
    verified_text, verifier_name = await verify_response(response_text, query_req.context or {})
    
    # Save query to database (WITHOUT model_used to fix error)
    # We store metadata (agent, verifier) in a JSON column
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
    
    # Schedule auto-delete (already handled by scheduler)
    
    return {
        "response": verified_text,
        "agent_used": agent_name,
        "verifier_used": verifier_name,
        "query_id": None  # We can return id if needed
    }

# ─── File Upload ──────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document and extract text."""
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
    """Transcribe an audio file (speech to text)."""
    content = await file.read()
    text = await transcribe_audio(content)
    return {"transcription": text}

# ─── Web Search ────────────────────────────────────────────────────
@app.post("/search")
async def search(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """Perform a web search and return snippets."""
    results = await web_search(query)
    return {"results": results}

# ─── Razorpay Payment Endpoints ──────────────────────────────────
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.post("/create-order")
async def create_order(
    payment_data: PaymentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a Razorpay order for subscription."""
    amount_map = {"premium": 10200, "enterprise": 101100}  # in paise
    if payment_data.tier not in amount_map:
        raise HTTPException(status_code=400, detail="Invalid tier")
    amount = amount_map[payment_data.tier]
    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })
    # Save order in DB
    await database.execute(
        payments.insert().values(
            user_id=current_user["id"],
            razorpay_order_id=order["id"],
            amount=amount/100,
            tier=payment_data.tier,
            status="created"
        )
    )
    return {"order_id": order["id"], "amount": amount, "currency": "INR"}

@app.post("/verify-payment")
async def verify_payment(
    razorpay_order_id: str = Form(...),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Verify payment and upgrade user."""
    params_dict = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        # Update payment status
        await database.execute(
            payments.update().where(payments.c.razorpay_order_id == razorpay_order_id).values(
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
                status="paid"
            )
        )
        # Get tier from payment
        payment = await database.fetch_one(
            payments.select().where(payments.c.razorpay_order_id == razorpay_order_id)
        )
        tier = payment["tier"]
        # Update user tier
        await database.execute(
            users.update().where(users.c.id == current_user["id"]).values(
                tier=tier,
                is_premium=True if tier != "free" else False
            )
        )
        return {"status": "success", "tier": tier}
    except:
        raise HTTPException(status_code=400, detail="Payment verification failed")

# ─── Admin / Health ──────────────────────────────────────────────
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