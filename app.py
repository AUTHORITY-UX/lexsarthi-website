# ===================================================================
# LEXSARTHI v5.0 – UNIVERSAL DEFAULT AI (PDF Library Ready)
# ===================================================================
# Owner: THE ADVOCACY – A LAW FIRM
# Deployed: upamnyu12-lex.hf.space
# ===================================================================

import os
import uuid
import json
import logging
import asyncio
import random
import string
import re
import glob
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# ─── FASTAPI ──────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
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

# ─── ENV VARIABLES ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ─── CLIENTS INIT ──────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')

# ─── DATABASE SETUP ─────────────────────────────────────────────
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
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
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

# =================================================================
# 🧠 UNIVERSAL DEFAULT LEGAL INTELLIGENCE (PDF LIBRARY LOADER)
# =================================================================
LEGAL_SECTIONS = {}  # {pdf_filename: {section_ref: section_text}}

def extract_sections_from_pdf(filepath: str) -> dict:
    """Extract text from a PDF and split into legal sections."""
    sections = {}
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        if not full_text.strip():
            logger.warning(f"Empty text extracted from {filepath}")
            return {}
        
        # Split by common legal section delimiters
        # Supports: Section, Sec., Article, Chapter, Clause, etc.
        section_pattern = r'(?=Section \d+\.?|Sec\. \d+\.?|Article \d+\.?|Chapter \d+\.?|Clause \d+\.?|§ \d+)'
        raw_sections = re.split(section_pattern, full_text)
        
        for i, sec in enumerate(raw_sections):
            if sec.strip():
                # Try to find the section title
                title_match = re.search(r'(Section \d+\.?|Sec\. \d+\.?|Article \d+\.?|Chapter \d+\.?|Clause \d+\.?|§ \d+)', sec)
                if title_match:
                    title = title_match.group(0)
                    # If the section already exists, append to it (handles multi-part sections)
                    if title in sections:
                        sections[title] += "\n" + sec
                    else:
                        sections[title] = sec
                else:
                    # If no title found but it's the first chunk (preamble), store it as "Preamble"
                    if i == 0:
                        sections["Preamble"] = sec[:1500]  # Limit preamble size
                    else:
                        # Try to assign a generic key
                        sections[f"Section_{i}"] = sec[:1000]
        
        logger.info(f"Extracted {len(sections)} sections from {os.path.basename(filepath)}")
    except Exception as e:
        logger.error(f"Failed to process {filepath}: {e}")
    
    return sections

def load_pdf_library():
    """Load all PDFs from the legal_docs folder."""
    pdf_dir = "/app/legal_docs/"
    if not os.path.exists(pdf_dir):
        logger.warning(f"Legal PDF library folder not found: {pdf_dir}")
        return
    
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found in legal_docs folder.")
        return
    
    logger.info(f"Found {len(pdf_files)} PDFs. Loading legal library...")
    for filepath in pdf_files:
        filename = os.path.basename(filepath)
        sections = extract_sections_from_pdf(filepath)
        if sections:
            LEGAL_SECTIONS[filename] = sections
    
    logger.info(f"✅ Universal Legal Library loaded: {len(LEGAL_SECTIONS)} PDFs, {sum(len(v) for v in LEGAL_SECTIONS.values())} sections total.")

# Load the library at startup
load_pdf_library()

def search_local_knowledge(query: str) -> str:
    """
    Search the entire PDF library for matching legal sections.
    This is the "Universal Default AI" fallback.
    """
    if not LEGAL_SECTIONS:
        return "⚠️ Legal library is not loaded. Please try again later."
    
    query_lower = query.lower()
    matched_results = []
    
    # Extract keywords from query (remove stopwords)
    stopwords = {"the", "a", "an", "of", "for", "on", "at", "to", "in", "with", "without", "and", "or", "but", "what", "how", "why", "when", "where"}
    keywords = [word for word in query_lower.split() if word not in stopwords and len(word) > 2]
    
    # If no keywords, just return the preamble of the first act
    if not keywords:
        for fname, sections in LEGAL_SECTIONS.items():
            if "Preamble" in sections:
                return f"📚 **From {fname.replace('.pdf', '')} (Preamble):**\n\n{sections['Preamble']}"
        return "📚 Please provide a more specific legal query."
    
    # Search through all sections across all PDFs
    for fname, sections in LEGAL_SECTIONS.items():
        act_name = fname.replace('.pdf', '').upper()
        for sec_ref, sec_text in sections.items():
            # Check if any keyword appears in the section text or reference
            sec_text_lower = sec_text.lower()
            if any(kw in sec_text_lower for kw in keywords):
                # Limit length to prevent massive output
                trimmed_text = sec_text[:2000] + "..." if len(sec_text) > 2000 else sec_text
                matched_results.append(f"📜 **{act_name} – {sec_ref}**\n{trimmed_text}\n")
                
                if len(matched_results) >= 5:  # Limit to 5 sections to avoid flooding
                    break
        if len(matched_results) >= 5:
            break
    
    if matched_results:
        result = "📚 **From Your Universal Legal Intelligence Library:**\n\n"
        result += "\n".join(matched_results)
        result += "\n\n*This is a fallback response from your local legal knowledge base (PDFs).*"
        return result
    
    # If no specific match, return the introduction of the most relevant act
    # Try to guess the act based on the query
    act_guesses = {
        "contract": "indian_contract_act.pdf",
        "criminal": "Bharatiya_Nagarik_Suraksha_Sanhita_2023.pdf",
        "constitution": "Constitution_act.pdf",
        "evidence": "Evidence_act.pdf",
        "company": "companies_act_2013.pdf",
        "it act": "it_act_2000.pdf",
        "data": "DATA_ACT.pdf",
        "dpdpa": "DPDPA.pdf",
        "arbitration": "the_arbitration_and_conciliation_act_1996.pdf",
        "advocate": "the_advocate_act_1961.pdf",
        "stamp": "the_indian_stamp_act_1899.pdf",
        "insolvency": "the_insolvency_and_bankruptcy_code_2016.pdf",
        "ai": "AI_ACT.pdf",
    }
    
    for guess_key, guess_file in act_guesses.items():
        if guess_key in query_lower:
            for fname, sections in LEGAL_SECTIONS.items():
                if guess_file in fname:
                    if "Preamble" in sections:
                        return f"📚 **From {fname.replace('.pdf', '').upper()} (Preamble - Relevant to your query):**\n\n{sections['Preamble'][:1500]}..."
                    # Return first section
                    first_key = list(sections.keys())[0]
                    return f"📚 **From {fname.replace('.pdf', '').upper()} (Section relevant to '{guess_key}'):**\n\n{sections[first_key][:1500]}..."
    
    # Ultimate fallback: return the first few sections of the first loaded PDF
    for fname, sections in LEGAL_SECTIONS.items():
        intro_text = "N/A"
        for key in ["Preamble", "Section 1", "Chapter 1"]:
            if key in sections:
                intro_text = sections[key]
                break
        return f"📚 **From {fname.replace('.pdf', '').upper()} (General Legal Intelligence):**\n\n{intro_text[:1500]}..."
    
    return "⚠️ No relevant legal sections found in your library. Please refine your query."

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
    filename = file.filename.lower()
    text = ""

    if filename.endswith('.pdf'):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            if len(reader.pages) == 0:
                raise ValueError("PDF has no pages.")
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if not text.strip():
                raise ValueError("PDF extraction returned empty text. The PDF may be scanned or image-based.")
            return text.strip()
        except Exception as e:
            raise ValueError(f"PDF processing failed: {str(e)}")

    elif filename.endswith('.docx'):
        try:
            doc = docx.Document(io.BytesIO(content))
            text = " ".join([p.text for p in doc.paragraphs])
            if not text.strip():
                raise ValueError("DOCX extraction returned empty text.")
            return text.strip()
        except Exception as e:
            raise ValueError(f"DOCX processing failed: {str(e)}")

    elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
        try:
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img)
            if not text.strip():
                raise ValueError("OCR returned no text. The image might be unclear.")
            return text.strip()
        except Exception as e:
            raise ValueError(f"Image OCR failed: {str(e)}")

    try:
        import puremagic
        mime = puremagic.from_string(content, mime=True)[0]
    except:
        mime = "application/octet-stream"

    if mime == "application/pdf":
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text += page.extract_text() or ""
            if text.strip():
                return text.strip()
        except:
            pass
        raise ValueError("The file appears to be a PDF but could not be processed. Try a text-based PDF.")
    elif "docx" in mime:
        try:
            doc = docx.Document(io.BytesIO(content))
            text = " ".join([p.text for p in doc.paragraphs])
            if text.strip():
                return text.strip()
        except:
            pass
        raise ValueError("The file appears to be a DOCX but could not be processed.")
    elif mime.startswith("image/"):
        try:
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img)
            if text.strip():
                return text.strip()
        except:
            pass
        raise ValueError("The file appears to be an image but could not be OCR processed.")

    try:
        text = content.decode('utf-8', errors='ignore')
        if text.strip():
            return text.strip()
    except:
        pass

    raise ValueError(f"Unsupported or unreadable file: {filename}. Please upload a PDF, DOCX, or image file.")

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
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://lexsarthi.ai"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": f"You are {agent_name}. {system_prompt}"},
                            {"role": "user", "content": query}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4096,
                    },
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")

    # 5. ULTIMATE FALLBACK: UNIVERSAL LEGAL INTELLIGENCE (PDF Library)
    logger.warning("All AI services failed. Falling back to Universal Legal Intelligence (PDF Library).")
    local_response = search_local_knowledge(query)
    return local_response

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
            if not file_text or len(file_text.strip()) < 20:
                raise HTTPException(status_code=400, detail="File is empty or contains no readable text.")
            combined_query = f"{query}\n\n--- Document Content ---\n{file_text}"
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"File processing failed: {str(e)}")

    if search_web.lower() in ("on", "yes"):
        combined_query += "\n\n--- Web Search Enabled ---"

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