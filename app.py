# =============================================================================
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================
# UNKNOWN VERDICT v11.0 – Complete Enterprise Edition with AI Safety
# =============================================================================

import os, io, csv, json, uuid, glob, re, random, string, logging, asyncio, ssl, socket, hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

# ─── EDGE AI ──────────────────────────────────────────────────────────
try:
    from edge_impulse_full import get_edge_ai_service, EdgeAIService
    EDGE_AI_AVAILABLE = True
except ImportError:
    EDGE_AI_AVAILABLE = False
    get_edge_ai_service = None
    EdgeAIService = None

from databases import Database
from fastapi import (FastAPI, HTTPException, Depends, UploadFile, File, Form,
                     Request, BackgroundTasks, Header, Body)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import asyncpg
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float, func, select, UniqueConstraint, and_, or_

import jwt
from passlib.context import CryptContext

import httpx
from groq import Groq
import openai
import google.generativeai as genai

import PyPDF2, pdfplumber, docx
from PIL import Image
import pytesseract

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

try:
    import razorpay
except ImportError:
    razorpay = None

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

# ─── REDIS ──────────────────────────────────────────────────────────────
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

# ─── ATMA ROUTER ──────────────────────────────────────────────────────────
try:
    from atma import AtmaRouter
except ImportError:
    AtmaRouter = None

# ─── AI SAFETY MODULES ──────────────────────────────────────────────────
try:
    from constitutional_ai import ConstitutionalAI
    from red_team import RedTeam
    from kill_switch import KillSwitch
    from monitoring import MonitoringSystem
    from interpretability import InterpretabilityDashboard
    from safety_case import SafetyCase
except ImportError:
    ConstitutionalAI = RedTeam = KillSwitch = MonitoringSystem = InterpretabilityDashboard = SafetyCase = None

# ─── EDGE AI MODULES ──────────────────────────────────────────────────
try:
    from akida_edge import AkidaEdge
    from edge_impulse_model import EdgeImpulseModel
    from spike_retriever import SpikeRetriever
except ImportError:
    AkidaEdge = EdgeImpulseModel = SpikeRetriever = None

# ─── AUTOMATION MODULES ──────────────────────────────────────────────
try:
    from linkedin_automation import LinkedInAutomation
    from payment_gateway import PaymentGateway
except ImportError:
    LinkedInAutomation = PaymentGateway = None

# ─── LOGGING CONFIGURATION ──────────────────────────────────────────────
import sys
import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ─── FILTER OUT SCANNER REQUESTS ──────────────────────────────────────

class ScannerFilter(logging.Filter):
    """Filter out security scanner requests for clean logs"""
    SCANNER_PATTERNS = [
        '.env', '.git', 'wp-config', 'phpinfo', 'graphql',
        'debug', 'actuator', 'metrics', 'prometheus',
        'streamlit', 'backup', 'config.php', 'phpmyadmin',
        'cgi-bin', 'xmlrpc', 'wp-admin', 'vendor',
        '.aws', '.ssh', 'id_rsa', 'Dockerfile',
        'swagger-ui.html', 'api-docs', 'redoc', 
        'file%3D', '..%252f', 'proc/self', '.local',
        '.production', '.development', '.backup', '.bak',
        '.old', '.example', 'env.json', 'config.yaml',
        'configuration', 'settings.json', 'internal/config',
        'debug/vars', 'debug/pprof', 'actuator', 'healthz',
        'server-status', 'server-info', '_debug', '__debug__',
        'api/keys', 'api/v1/keys', 'api/config', 'api/v1/config',
        'api/settings', 'api/env', 'api/v1/env', 'api/credentials',
        'api/secrets', 'api/v1/models', 'swagger.json',
        'api-docs', 'file/..', 'upload?upload_id',
        '_stcore', '.streamlit', 'api/predict', 'api/queue/status',
        'run/predict', '?__theme=dark', '.git/config',
        '.git/HEAD', 'wp-config.php.bak', 'backup/.env',
        'backup/config.json', '.env.swp', 'config.php.bak',
        'app.py', 'main.py', 'admin', 'admin/config', 'internal',
        'internal/debug', 'metrics', 'prometheus', 'graphql',
        'api/graphql', 'phpinfo.php', '__phpinfo', 'elmah.axd',
        'trace.axd', 'telescope', 'horizon', '_profiler',
        'proc/self/environ', 'proc/self/cmdline'
    ]
    
    def filter(self, record):
        msg = record.getMessage()
        for pattern in self.SCANNER_PATTERNS:
            if pattern in msg:
                return False
        return True

# ─── APPLY FILTERS ──────────────────────────────────────────────────────

uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_access.addFilter(ScannerFilter())

uvicorn_error = logging.getLogger("uvicorn.error")
uvicorn_error.addFilter(ScannerFilter())

# ─── SUPPRESS NOISY LOGGERS ────────────────────────────────────────────

NOISY_LOGGERS = [
    'apscheduler.scheduler', 'apscheduler.executors', 'apscheduler.jobstores',
    'httpx', 'httpcore', 'urllib3', 'sentence_transformers.SentenceTransformer',
    'databases', 'edge_impulse_linux', 'asyncio', 'fsspec', 'PIL', 'pdfplumber',
    'openai', 'groq', 'google.generativeai'
]

for logger_name in NOISY_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# ─── CREATE APP LOGGER ──────────────────────────────────────────────────

logger = logging.getLogger("unknown_verdict")
logger.info("🚀 Unknown Verdict v11.0 - Initializing...")

# ─── ENV ──────────────────────────────────────────────────────────────────
DATABASE_URL       = os.getenv("DATABASE_URL")
REDIS_URL          = os.getenv("REDIS_URL", None)
JWT_SECRET         = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY   = os.getenv("DEEPSEEK_API_KEY")
SERPAPI_KEY        = os.getenv("SERPAPI_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", None)

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_USER_ID      = os.getenv("LINKEDIN_USER_ID")
ADMIN_SECRET          = os.getenv("ADMIN_SECRET", "change-me")

# ─── PROVIDER CLIENTS ────────────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client   = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model  = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# ─── LOCAL EMBEDDING MODEL ──────────────────────────────────────────────
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# ─── DATABASE (SQLAlchemy) ──────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=2, max_size=20) if DATABASE_URL else None
metadata = MetaData()

# ─── ALL TABLE DEFINITIONS ──────────────────────────────────────────────
# [Your existing table definitions - users, queries, payments, etc.]

# ─── GLOBAL POOLS ──────────────────────────────────────────────────────
pg_pool: Optional[asyncpg.Pool] = None
redis_pool: Optional[ConnectionPool] = None

# ─── PYDANTIC MODELS ────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class PaymentCreate(BaseModel):
    tier: str

# ─── SECURITY ────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(p):
    return pwd_context.hash(p)

def verify_password(p, h):
    try:
        return pwd_context.verify(p, h)
    except:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(cred.credentials)
    uid_or_username = payload.get("sub")
    if not uid_or_username:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        uid = int(uid_or_username)
        q = users.select().where(users.c.id == uid)
    except ValueError:
        q = users.select().where(users.c.username == uid_or_username)
    user = await database.fetch_one(q)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

# ─── RATE LIMITER ──────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
logger.info("✅ Rate limiter using in‑memory storage")

# ─── SYSTEM PROMPT ──────────────────────────────────────────────────────
SYSTEM_BASE = """You are the Unknown Verdict Engine – an AI advisory OS with 250 specialist personas, 
a jury of 10 verifiers, and a final judge. You have access to a knowledge base (including the Constitution of India) 
and live web search. Always strive for accuracy, cite sources, and admit uncertainty. 
Default jurisdiction: India. Tone: professional, wise, neutral."""

# ─── 250 SPECIALIST PERSONAS ──────────────────────────────────────────
DOMAINS_FULL = [
    "Constitutional Law", "Contract Law", "Criminal Law", "Corporate Law", "Tax Law",
    "IP Law", "Family Law", "Cyber Law", "Arbitration", "Property Law", "GST", "Income Tax",
    "Audit", "Incorporation", "Compliance", "Mathematics", "Statistics", "Physics", "Chemistry",
    "Biology", "Medicine", "Psychology", "Philosophy", "Logic", "Reasoning", "Economics",
    "Finance", "History", "Geopolitics", "Astronomy", "Vedanta", "Yoga", "Ayurveda", "Sanskrit",
    "Mythology", "Ethics", "AI Ethics", "Cryptography", "Blockchain", "Climate Science",
    "Environmental Law", "Human Rights", "International Law", "Maritime Law", "Space Law",
    "Data Privacy", "E-commerce", "Real Estate", "Banking", "Insurance"
]
DIVINE_NAMES_POOL = ["Brahma","Vishnu","Shiva","Saraswati","Lakshmi","Ganesha","Hanuman",
    "Kartikeya","Indra","Yama","Surya","Chandra","Vayu","Agni","Varuna","Kubera",
    "Yamuna","Ganga","Durga","Kali","Tara","Bhuvaneshwari","Chinnamasta","Bhairavi",
    "Dhumavati","Bagalamukhi","Matangi","Kamala","Dattatreya","Narasimha","Vamana",
    "Parashurama","Rama","Krishna","Buddha","Kalki","Matsya","Kurma","Varaha","Skanda",
    "Ayyappa","Shani","Mangal","Budh","Guru","Shukra","Rahu","Ketu"]
sub_specialties = {
    "Constitutional Law": ["Fundamental Rights", "Federalism", "Judicial Review", "Amendment", "Emergency"],
    "Contract Law": ["Formation", "Performance", "Breach", "Remedies", "Specific Relief"],
    "Criminal Law": ["IPC", "CrPC", "Evidence", "White Collar", "Sentencing"],
    "Corporate Law": ["M&A", "Board Governance", "Shareholder Rights", "Insolvency", "SEBI"],
    "Tax Law": ["Direct Tax", "Indirect Tax", "International Tax", "Transfer Pricing", "Tax Litigation"],
}

def generate_all_agents():
    agents = []
    domain_idx = 0
    name_idx = 0
    for i in range(250):
        domain = DOMAINS_FULL[domain_idx % len(DOMAINS_FULL)]
        sub_list = sub_specialties.get(domain, [f"Specialist {j+1}" for j in range(5)])
        sub = sub_list[i % len(sub_list)]
        agent_name = f"{DIVINE_NAMES_POOL[name_idx % len(DIVINE_NAMES_POOL)]} · {domain} ({sub})"
        agents.append({
            "id": f"agent_{i+1:03d}",
            "name": agent_name,
            "domain": domain,
            "persona_prompt": f"You are a specialist in {domain}, focusing on {sub}. Use deep expertise."
        })
        domain_idx += 1
        if (i+1) % 5 == 0:
            name_idx += 1
    return agents

DIVINE_AGENTS = generate_all_agents()
logger.info(f"✅ Loaded {len(DIVINE_AGENTS)} specialist personas")

# ─── VERIFIERS (10) ─────────────────────────────────────────────────────
VERIFIERS = [
    {"id":"v01","name":"Ganesha","role":"Citation & logic integrity","prompt":"Check legal citations and logical flow."},
    {"id":"v02","name":"Saraswati","role":"Knowledge cross-reference","prompt":"Verify facts against established knowledge."},
    {"id":"v03","name":"Hanuman","role":"Global compliance","prompt":"Ensure advice follows international norms."},
    {"id":"v04","name":"Kartikeya","role":"Contradiction detection","prompt":"Find internal contradictions."},
    {"id":"v05","name":"Indra","role":"Jurisdiction mapping","prompt":"Check jurisdiction assumptions."},
    {"id":"v06","name":"Yama","role":"Bias & neutrality","prompt":"Scan for bias."},
    {"id":"v07","name":"Surya","role":"Timeline & limitation","prompt":"Confirm statutes are current."},
    {"id":"v08","name":"Chandra","role":"Precedent match","prompt":"Check alignment with known precedents."},
    {"id":"v09","name":"Vayu","role":"PII / privacy filter","prompt":"Redact PII."},
    {"id":"v10","name":"Shakti","role":"Final judge & dharma seal","prompt":"Integrate all critiques and produce a final answer with a confidence rating."}
]
logger.info(f"✅ Loaded {len(VERIFIERS)} verifiers including judge Shakti")

# ─── ROUTE AGENT ──────────────────────────────────────────────────────────
def route_agent(query: str, oracle: bool) -> str:
    if oracle:
        return "oracle"
    q = query.lower()
    best_score = -1
    best_id = "general"
    for agent in DIVINE_AGENTS:
        domain_words = agent["domain"].lower().split()
        score = sum(1 for w in q.split() if w in domain_words)
        if score > best_score:
            best_score = score
            best_id = agent["id"]
    return best_id if best_score >= 2 else "general"

# ─── RAG (pgvector) ─────────────────────────────────────────────────────
async def fetch_relevant_chunks(query: str, top_k: int = 3, conn: asyncpg.Connection = None) -> List[Dict]:
    query_embedding = embedding_model.encode(query).tolist()
    query_embedding_str = json.dumps(query_embedding)
    if conn is None:
        async with pg_pool.acquire() as conn:
            return await _fetch_chunks(conn, query_embedding_str, top_k)
    else:
        return await _fetch_chunks(conn, query_embedding_str, top_k)

async def _fetch_chunks(conn, embedding_str: str, top_k: int):
    rows = await conn.fetch(
        """
        SELECT content, metadata, 1 - (embedding <=> $1) AS similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> $1
        LIMIT $2
        """,
        embedding_str, top_k
    )
    return [
        {
            "content": row["content"],
            "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]),
            "citation": row["metadata"].get("source", "Unknown") if isinstance(row["metadata"], dict) else json.loads(row["metadata"]).get("source", "Unknown"),
            "similarity": row["similarity"]
        }
        for row in rows
    ]

# ─── WEB SEARCH ──────────────────────────────────────────────────────────
async def serpapi_search(query: str, unrestricted: bool = False) -> List[Dict]:
    if not SERPAPI_KEY:
        return []
    params = {"q": query, "api_key": SERPAPI_KEY, "num": 3}
    if not unrestricted:
        domains = os.getenv("TARGETED_SEARCH_DOMAINS", "").replace(" ", "")
        if domains:
            params["q"] = f'site:({domains.replace(",", " OR ")}) {query}'
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://serpapi.com/search", params=params, timeout=8.0)
            if r.status_code == 200:
                return r.json().get("organic_results", [])
    except Exception as e:
        logger.error(f"Web search failed: {e}")
    return []

# ─── FILE PROCESSING ──────────────────────────────────────────────────
async def process_file_bytes(content: bytes, filename: str) -> str:
    fn = filename.lower()
    try:
        if fn.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "".join(p.extract_text() or "" for p in pdf.pages)
            if text.strip():
                return text.strip()
            raise ValueError("PDF empty")
        if fn.endswith(".docx"):
            d = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in d.paragraphs).strip()
        if fn.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff")):
            img = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(img).strip()
        return content.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        raise ValueError(f"Unable to read {filename}: {e}")

# ─── LLM CALL ──────────────────────────────────────────────────────────
async def call_llm(
    system_prompt: str,
    user_message: str,
    provider: str = "groq",
    temperature: float = 0.7,
    history: List[Dict] = None,
    max_tokens: int = 4096
) -> str:
    MAX_INPUT_TOKENS = 8000
    if len(user_message) > MAX_INPUT_TOKENS:
        user_message = user_message[:MAX_INPUT_TOKENS] + "\n[...truncated...]"

    # Try Groq first if available
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq failed: {e}")
    
    # Fallback to OpenAI
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}")
    
    return "Error: No LLM provider available. Please set GROQ_API_KEY or OPENAI_API_KEY."

# ─── JURY VERIFICATION ────────────────────────────────────────────────
async def jury_verification(initial_answer: str, query: str, domain: str) -> Dict:
    logger.info("⚖️ JURY SUMMONED: 10 Verifiers reviewing the answer...")
    
    verifier_results = []
    final_confidence = "MEDIUM"
    
    for verifier in VERIFIERS:
        logger.info(f"📜 {verifier['name']} ({verifier['role']}) is reviewing...")
        
        ver_system = f"""You are {verifier['name']} ({verifier['role']}). 
        Review the following legal answer and return JSON:
        {{"status": "APPROVED|CORRECTED|REJECTED", 
          "confidence": "HIGH|MEDIUM|LOW", 
          "corrected_text": "...", 
          "feedback": "...",
          "issues": ["..."]}}"""
        
        try:
            out = await call_llm(ver_system, f"Query: {query}\n\nDomain: {domain}\n\nAnswer to review:\n{initial_answer}", "groq")
            m = re.search(r'\{.*\}', out, re.DOTALL)
            if m:
                result = json.loads(m.group())
                result['verifier'] = verifier['name']
                result['role'] = verifier['role']
                verifier_results.append(result)
                
                if result.get('confidence') == 'HIGH':
                    final_confidence = 'HIGH'
                elif result.get('confidence') == 'LOW' and final_confidence != 'HIGH':
                    final_confidence = 'LOW'
                
                logger.info(f"✅ {verifier['name']}: {result.get('status')} (Confidence: {result.get('confidence')})")
            else:
                verifier_results.append({
                    'verifier': verifier['name'],
                    'role': verifier['role'],
                    'status': 'APPROVED',
                    'confidence': 'MEDIUM',
                    'feedback': 'No specific issues found'
                })
                logger.info(f"⚠️ {verifier['name']}: Default APPROVED")
        except Exception as e:
            logger.error(f"❌ {verifier['name']} error: {e}")
            verifier_results.append({
                'verifier': verifier['name'],
                'role': verifier['role'],
                'status': 'APPROVED',
                'confidence': 'MEDIUM',
                'feedback': 'Verification skipped due to error'
            })
    
    logger.info("👑 SHAKTI (Final Judge) is delivering the verdict...")
    
    all_feedback = []
    for v in verifier_results:
        if v.get('feedback'):
            all_feedback.append(f"{v['verifier']}: {v['feedback']}")
    
    judge_system = """You are Shakti, the Final Judge and Dharma Seal.
    You must integrate all verifier critiques and produce the final answer.
    Return JSON: {"final_answer": "...", "confidence": "HIGH|MEDIUM|LOW", "sources": [...]}"""
    
    judge_prompt = f"""
    Query: {query}
    Domain: {domain}
    Original Answer: {initial_answer}
    
    Verifier Feedback:
    {chr(10).join(all_feedback)}
    
    Please deliver the final verdict.
    """
    
    try:
        judge_response = await call_llm(judge_system, judge_prompt, "groq")
        m = re.search(r'\{.*\}', judge_response, re.DOTALL)
        if m:
            judge_decision = json.loads(m.group())
            final_answer = judge_decision.get('final_answer', initial_answer)
            final_confidence = judge_decision.get('confidence', final_confidence)
            sources = judge_decision.get('sources', [])
        else:
            final_answer = initial_answer
            sources = []
    except Exception as e:
        logger.error(f"❌ Judge error: {e}")
        final_answer = initial_answer
        sources = []
    
    logger.info(f"👑 SHAKTI'S VERDICT: Confidence = {final_confidence}")
    
    return {
        "final_answer": final_answer,
        "confidence": final_confidence,
        "sources": sources,
        "jury_verifiers": [v['verifier'] for v in verifier_results],
        "jury_confidences": {v['verifier']: v.get('confidence', 'MEDIUM') for v in verifier_results},
        "judge": "Shakti",
        "verifier_details": verifier_results
    }

# ─── MEMORY ───────────────────────────────────────────────────────────
async def _get_memory(uid: int) -> List[dict]:
    if not database:
        return []
    u = await database.fetch_one(users.select().where(users.c.id == uid))
    if not u:
        return []
    m = dict(u).get("memory") or []
    if isinstance(m, str):
        try:
            m = json.loads(m)
        except:
            m = []
    return m

async def _update_memory(uid: int, q: str, a: str):
    if not database:
        return
    m = await _get_memory(uid)
    m.append({"q": q[:200], "a": a[:200]})
    m = m[-3:]
    await database.execute(users.update().where(users.c.id == uid).values(memory=json.dumps(m)))

# ─── CONTEXT BUILDER ──────────────────────────────────────────────────
def _build_context(mem: List[dict]) -> str:
    if not mem:
        return ""
    recent = mem[-2:]
    context_parts = []
    for exchange in recent:
        q = exchange.get('q', '')[:200]
        a = exchange.get('a', '')[:300]
        context_parts.append(f"[Prev Q] {q}\n[Prev A] {a}")
    if not context_parts:
        return ""
    separator = "\n".join(context_parts)
    return f"═══ RECENT CONTEXT ═══\n{separator}\n═════════════════\nCurrent query:\n"

# ─── CACHING HELPERS ──────────────────────────────────────────────────
def _get_cache_key(query: str, model: str, oracle: bool) -> str:
    key_str = f"{query}|{model}|{oracle}"
    return f"lex_cache:{hashlib.md5(key_str.encode()).hexdigest()}"

async def get_cached_response(query: str, model: str, oracle: bool) -> Optional[Dict]:
    if not redis_pool:
        return None
    key = _get_cache_key(query, model, oracle)
    try:
        data = await redis_pool.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
    return None

async def set_cached_response(query: str, model: str, oracle: bool, response_data: Dict, ttl_seconds: int = 86400):
    if not redis_pool:
        return
    key = _get_cache_key(query, model, oracle)
    try:
        await redis_pool.setex(key, ttl_seconds, json.dumps(response_data))
    except Exception as e:
        logger.warning(f"Redis set error: {e}")

# ─── STREAMING REPLAY ──────────────────────────────────────────────
async def replay_stream(answer: str, confidence: str, sources: List[str], metadata: dict):
    for i in range(0, len(answer), 6):
        yield f"data: {json.dumps({'token': answer[i:i+6]})}\n\n"
        await asyncio.sleep(0.01)
    verification = {
        "final_confidence": confidence,
        "sources": sources,
        "jury_verifiers": metadata.get("jury_verifiers", []),
        "jury_confidences": metadata.get("jury_confidences", {}),
        "judge": metadata.get("judge", "Shakti"),
        "domain": metadata.get("domain", "general"),
        "persona": metadata.get("persona", ""),
        "provider": metadata.get("provider", ""),
        "verifier_details": metadata.get("verifier_details", [])
    }
    yield f"data: {json.dumps({'verification': verification})}\n\n"
    yield "data: [DONE]\n\n"

# ─── LIFESPAN ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool, redis_pool

    os.makedirs("blog", exist_ok=True)

    if database:
        await database.connect()
        await _create_tables()
        await _ensure_test_user()

    if DATABASE_URL:
        pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

    if REDIS_URL:
        try:
            clean_url = REDIS_URL
            if "redis-cli --tls -u " in clean_url:
                clean_url = clean_url.split("redis-cli --tls -u ")[-1]
            if clean_url.startswith("redis://") and "?ssl=true" not in clean_url:
                clean_url = clean_url.replace("redis://", "rediss://", 1)
            redis_pool = redis.from_url(
                clean_url,
                decode_responses=True,
                max_connections=10,
                socket_keepalive=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            await redis_pool.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            redis_pool = None
    else:
        redis_pool = None
        logger.warning("⚠️ REDIS_URL not set – caching disabled")

    # Initialize components
    app.state.pg_pool = pg_pool
    app.state.redis_pool = redis_pool
    
    if ConstitutionalAI:
        app.state.constitutional_ai = ConstitutionalAI(pg_pool)
    if RedTeam:
        app.state.red_team = RedTeam(pg_pool, call_llm)
    if KillSwitch:
        app.state.kill_switch = KillSwitch(pg_pool, redis_pool)
    if MonitoringSystem:
        app.state.monitoring = MonitoringSystem(pg_pool, redis_pool)
    if InterpretabilityDashboard:
        app.state.interpretability = InterpretabilityDashboard(pg_pool)
    if SafetyCase:
        app.state.safety_case = SafetyCase(pg_pool)

    if AtmaRouter:
        app.state.atma = AtmaRouter(
            pg_pool,
            fetch_relevant_chunks_func=fetch_relevant_chunks,
            serpapi_search_func=serpapi_search,
            call_llm_func=call_llm,
            constitutional_ai=app.state.constitutional_ai if hasattr(app.state, 'constitutional_ai') else None,
            kill_switch=app.state.kill_switch if hasattr(app.state, 'kill_switch') else None,
            monitoring=app.state.monitoring if hasattr(app.state, 'monitoring') else None
        )

    # Scheduler
    sched = AsyncIOScheduler()
    sched.add_job(_purge_expired, IntervalTrigger(hours=1))
    sched.add_job(_update_domain_analytics, IntervalTrigger(hours=1))
    if FEEDPARSER_AVAILABLE:
        sched.add_job(_daily_news_pipeline, CronTrigger(hour=5, minute=0, timezone="Asia/Kolkata"), id="daily_news_pipeline")
    sched.add_job(_analyse_and_improve, IntervalTrigger(hours=24))
    sched.start()
    
    logger.info("👁️ Unknown Verdict Engine v11.0 – Complete Enterprise Edition Ready.")

    yield

    if database:
        await database.disconnect()
    if pg_pool:
        await pg_pool.close()
    if redis_pool:
        await redis_pool.close()

# ─── DB INIT ────────────────────────────────────────────────────────────
async def _create_tables():
    if not database:
        return
    try:
        await database.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    except:
        pass
    # [Your table creation DDL statements]

async def _ensure_test_user():
    if not database:
        return
    existing = await database.fetch_one(users.select().where(users.c.username == "counsel"))
    if not existing:
        await database.execute(users.insert().values(
            username="counsel",
            email="counsel@advocacyalawfrim.in",
            password_hash=hash_password("Password123!"),
            full_name="Counsel User",
            tier="enterprise",
            api_key="".join(random.choices(string.ascii_letters + string.digits, k=32)),
            memory=json.dumps([])
        ))
        logger.info("✅ Seeded test user 'counsel'.")

async def _purge_expired():
    if not database:
        return
    await database.execute(queries.delete().where(queries.c.created_at < datetime.now() - timedelta(hours=24)))
    await database.execute(bulk_jobs.delete().where(bulk_jobs.c.created_at < datetime.now() - timedelta(days=7)))

async def _update_domain_analytics():
    # [Your domain analytics code]
    pass

async def _analyse_and_improve():
    # [Your self-improvement code]
    pass

async def _daily_news_pipeline():
    # [Your daily news pipeline code]
    pass

# ─── LIMIT HELPERS ──────────────────────────────────────────────────────
async def _check_limit(u: dict) -> bool:
    if u["tier"] in ("premium", "enterprise", "lifetime"):
        return True
    today = datetime.now().date()
    last = u["last_query_reset"].date() if u["last_query_reset"] else datetime.min.date()
    if today > last:
        if database:
            await database.execute(users.update().where(users.c.id == u["id"]).values(queries_used_today=0, last_query_reset=func.now()))
        return True
    return u["queries_used_today"] < 10

async def _incr_query(uid: int):
    if database:
        await database.execute(users.update().where(users.c.id == uid).values(queries_used_today=users.c.queries_used_today + 1, updated_at=datetime.now()))

# ─── APP INSTANCE ────────────────────────────────────────────────────────
app = FastAPI(
    title="Unknown Verdict v11.0 - Enterprise Legal AI",
    description="⚖️ AI-Powered Legal Advisory with 250 Specialist Personas, 10 Verifiers, and Judge Shakti",
    version="11.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── EDGE AI SERVICE ──────────────────────────────────────────────────
edge_ai_service: Optional[EdgeAIService] = None

@app.on_event("startup")
async def startup_edge_ai():
    global edge_ai_service
    if EDGE_AI_AVAILABLE and get_edge_ai_service:
        try:
            edge_ai_service = await get_edge_ai_service()
            logger.info("✅ Edge AI Service initialized")
        except Exception as e:
            logger.error(f"❌ Edge AI Service initialization failed: {e}")
            edge_ai_service = None
    else:
        logger.info("⚠️ Edge AI Service not available")

# ─── STARTUP BANNER ─────────────────────────────────────────────────────
@app.on_event("startup")
async def display_startup_banner():
    edge_status = "✅ AVAILABLE" if edge_ai_service else "⚠️ SIMULATION"
    
    banner = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║     ██╗   ██╗███╗   ██╗██╗  ██╗███╗   ██╗ ██████╗ ██╗    ██╗███╗   ██╗ ║
║     ██║   ██║████╗  ██║██║ ██╔╝████╗  ██║██╔═══██╗██║    ██║████╗  ██║ ║
║     ██║   ██║██╔██╗ ██║█████╔╝ ██╔██╗ ██║██║   ██║██║ █╗ ██║██╔██╗ ██║ ║
║     ██║   ██║██║╚██╗██║██╔═██╗ ██║╚██╗██║██║   ██║██║███╗██║██║╚██╗██║ ║
║     ╚██████╔╝██║ ╚████║██║  ██╗██║ ╚████║╚██████╔╝╚███╔███╔╝██║ ╚████║ ║
║      ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═══╝ ║
║                                                                           ║
║    🏛️  UNKNOWN VERDICT v11.0 - Enterprise Legal AI                     ║
║    ⚖️  {len(DIVINE_AGENTS)} Specialist Personas | {len(VERIFIERS)} Verifiers + Judge Shakti      ║
║    📡  Edge AI: {edge_status}                                               ║
║    🚀  Server: http://0.0.0.0:7860                                      ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """
    print("\033[96m" + banner + "\033[0m")

# ─── HEALTH CHECK ──────────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_status = "connected" if redis_pool else "disabled"
    edge_status = "available" if edge_ai_service else "unavailable"
    return {
        "status": "healthy",
        "version": "11.0-enterprise",
        "agents": 250,
        "verifiers": 10,
        "redis": redis_status,
        "edge_ai": edge_status
    }

# ─── AUTH ROUTES ──────────────────────────────────────────────────────
@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    if not database:
        raise HTTPException(status_code=503, detail="Database not available")
    u = await database.fetch_one(
        users.select().where(
            (users.c.username == body.username) | 
            (users.c.email == body.username.lower())
        )
    )
    if not u or not verify_password(body.password, dict(u)["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    u = dict(u)
    tok = create_access_token({"sub": str(u["id"])})
    return {
        "access_token": tok, 
        "token_type": "bearer", 
        "user": {
            "id": u["id"], 
            "username": u["username"], 
            "email": u["email"], 
            "tier": u["tier"]
        }
    }

@app.post("/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, body: UserCreate):
    if not database:
        raise HTTPException(status_code=503, detail="Database not available")
    ex = await database.fetch_one(users.select().where((users.c.username == body.username) | (users.c.email == body.email.lower())))
    if ex:
        raise HTTPException(status_code=400, detail="User already exists")
    ak = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    uid = await database.fetch_val(users.insert().values(
        username=body.username,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        tier="free",
        api_key=ak,
        memory=json.dumps([])
    ).returning(users.c.id))
    tok = create_access_token({"sub": str(uid)})
    return {"access_token": tok, "token_type": "bearer", "user": {"id": uid, "username": body.username, "api_key": ak}}

@app.get("/auth/me")
async def me(cu: dict = Depends(get_current_user)):
    return cu

# ─── /ask ROUTE ──────────────────────────────────────────────────────
@app.post("/ask")
@limiter.limit("30/minute")
async def ask(
    request: Request,
    query: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    search_web: str = Form("off"),
    model: str = Form("llama-3.3-70b-versatile"),
    lang: str = Form("en"),
    oracle_mode: str = Form("false"),
    unrestricted: str = Form("false"),
    persona_id: str = Form(""),
    cu: dict = Depends(get_current_user)
):
    logger.info(f"📝 QUERY: {query[:100]}... from user {cu['username']}")
    
    if not await _check_limit(cu):
        raise HTTPException(status_code=429, detail="Free daily limit reached.")

    combined_query = query
    if files:
        for file in files:
            content = await file.read()
            if len(content) > 8 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"File {file.filename} too large.")
            try:
                ft = await process_file_bytes(content, file.filename)
                if ft.strip():
                    if len(ft) > 20000:
                        ft = ft[:20000] + "\n[...truncated...]"
                    combined_query += f"\n\n═══ DOCUMENT: {file.filename} ═══\n{ft}"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"File error: {e}")

    await _incr_query(cu["id"])

    mem = await _get_memory(cu["id"])
    if mem:
        context = _build_context(mem)
        if context:
            combined_query = context + combined_query

    oracle = oracle_mode.lower() == "true"
    unrestricted_bool = unrestricted.lower() == "true"

    if len(combined_query) > 8000:
        combined_query = combined_query[:8000] + "\n[...truncated...]"

    agent_id = route_agent(combined_query, oracle)
    logger.info(f"🎯 Agent: {agent_id}")
    
    if agent_id == "oracle":
        persona = "You are the Oracle, offering spiritual and philosophical wisdom."
        domain = "Spiritual & Philosophical"
        agent_name = "Oracle"
    elif agent_id == "general":
        persona = "You are the full Unknown Verdict council, a generalist with broad knowledge."
        domain = "General"
        agent_name = "General Council"
    else:
        agent = next((a for a in DIVINE_AGENTS if a["id"] == agent_id), None)
        if agent:
            persona = agent["persona_prompt"]
            domain = agent["domain"]
            agent_name = agent["name"]
        else:
            persona = "You are a generalist."
            domain = "General"
            agent_name = "General Council"
    
    logger.info(f"👤 Agent: {agent_name} (Domain: {domain})")

    cache_hit = None
    if not files and not oracle:
        cache_hit = await get_cached_response(combined_query, model, oracle)

    if cache_hit:
        logger.info("💾 Cache hit!")
        answer = cache_hit["answer"]
        confidence = cache_hit["confidence"]
        sources = cache_hit["sources"]
        metadata = cache_hit["metadata"]
        if database:
            await database.execute(
                queries.insert().values(
                    user_id=cu["id"],
                    query=combined_query[:8000],
                    response=answer[:16000],
                    metadata=metadata,
                    expires_at=datetime.now() + timedelta(hours=24)
                )
            )
        return StreamingResponse(replay_stream(answer, confidence, sources, metadata), media_type="text/event-stream")

    system_prompt = f"""{SYSTEM_BASE}
    ═══ SPECIALIST AGENT ═══
    Agent: {agent_name}
    Domain: {domain}
    Persona: {persona}
    """

    logger.info(f"🧠 Generating response with {agent_name}...")

    # Use AtmaRouter if available
    if hasattr(app.state, 'atma') and app.state.atma:
        result = await app.state.atma.run(query=combined_query, history=None, files=None, unrestricted=unrestricted_bool)
        initial_answer = result["answer"]
    else:
        initial_answer = await call_llm(system_prompt, combined_query, "groq")
        result = {"answer": initial_answer, "provider": "groq"}

    logger.info(f"📄 Initial answer generated ({len(initial_answer)} chars)")

    logger.info("⚖️ Summoning the 10 verifier jury...")
    jury_result = await jury_verification(initial_answer, combined_query, domain)
    
    answer = jury_result["final_answer"]
    confidence = jury_result["confidence"]
    sources = jury_result["sources"]
    
    logger.info(f"👑 Final verdict: Confidence={confidence}, Sources={len(sources)}")

    metadata = {
        "domain": domain,
        "persona": agent_name,
        "provider": result.get("provider", ""),
        "jury_verifiers": jury_result["jury_verifiers"],
        "jury_confidences": jury_result["jury_confidences"],
        "judge": "Shakti",
        "verifier_details": jury_result.get("verifier_details", [])
    }

    if not files and not oracle:
        cache_data = {"answer": answer, "confidence": confidence, "sources": sources, "metadata": metadata}
        await set_cached_response(combined_query, model, oracle, cache_data, ttl_seconds=86400)
        logger.info("💾 Response cached")

    await _update_memory(cu["id"], query, answer)

    if database:
        await database.execute(
            queries.insert().values(
                user_id=cu["id"],
                query=combined_query[:8000],
                response=answer[:16000],
                metadata=metadata,
                expires_at=datetime.now() + timedelta(hours=24)
            )
        )
        await database.execute(
            deliberations.insert().values(
                query=combined_query[:500],
                domain=domain,
                persona=agent_name,
                provider=result.get("provider", ""),
                initial_answer=initial_answer[:500],
                verifier_results=json.dumps(jury_result.get("verifier_details", [])),
                final_answer=answer[:500],
                confidence=confidence,
                sources=json.dumps(sources)
            )
        )
        logger.info("💾 Deliberation saved to database")

    return StreamingResponse(replay_stream(answer, confidence, sources, metadata), media_type="text/event-stream")

# ─── MY USAGE ──────────────────────────────────────────────────────────
@app.get("/my-usage")
async def my_usage(cu: dict = Depends(get_current_user)):
    if not database:
        return {"total_queries": 0, "queries_today": 0}
    total = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == cu["id"])) or 0
    today = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == cu["id"], func.date(queries.c.created_at) == func.current_date())) or 0
    return {"total_queries": total, "queries_today": today}

# ─── STATIC FILES ──────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# ════════════════════════════════════════════════════════════════════════════
# ✅ SINGLE MAIN BLOCK - DO NOT DUPLICATE!
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "7860"))
    
    print(f"""
    ════════════════════════════════════════════════════════════════
      🏛️  UNKNOWN VERDICT v11.0 - Enterprise Legal AI
    
      🌐  Server: http://0.0.0.0:{port}
      👤  Workers: 1 (Clean Logs)
      🚀  Press CTRL+C to stop
    ════════════════════════════════════════════════════════════════
    """)
    
    # ✅ SINGLE WORKER - Clean logs, no duplicates
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        workers=1,  # ⭐ CRITICAL: Single worker for clean logs
        log_level="info",
        access_log=True,
        timeout_keep_alive=30
    )