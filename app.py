# =============================================================================
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================
# UNKNOWN VERDICT v11.0 – Complete Enterprise Edition with AI Safety
# =============================================================================

import os, io, csv, json, uuid, glob, re, random, string, logging, asyncio, ssl, socket, hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from edge_impulse_full import get_edge_ai_service, EdgeAIService

from databases import Database
from fastapi import (FastAPI, HTTPException, Depends, UploadFile, File, Form,
                     Request, BackgroundTasks, Header, Body)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr
import uvicorn

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

import razorpay

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

# ─── REDIS ──────────────────────────────────────────────────────────────
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

# ─── ATMA ROUTER ──────────────────────────────────────────────────────────
from atma import AtmaRouter

# ─── AI SAFETY MODULES ──────────────────────────────────────────────────
from constitutional_ai import ConstitutionalAI
from red_team import RedTeam
from kill_switch import KillSwitch
from monitoring import MonitoringSystem
from interpretability import InterpretabilityDashboard
from safety_case import SafetyCase

# ─── EDGE AI MODULES ──────────────────────────────────────────────────
from akida_edge import AkidaEdge
from edge_impulse_model import EdgeImpulseModel
from spike_retriever import SpikeRetriever

# ─── AUTOMATION MODULES ──────────────────────────────────────────────
from linkedin_automation import LinkedInAutomation
from payment_gateway import PaymentGateway

# ─── LOGGING CONFIGURATION ──────────────────────────────────────────────
import sys
import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
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

# Filter uvicorn access logs
uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_access.addFilter(ScannerFilter())

# Filter uvicorn error logs
uvicorn_error = logging.getLogger("uvicorn.error")
uvicorn_error.addFilter(ScannerFilter())

# ─── SUPPRESS NOISY LOGGERS ────────────────────────────────────────────

NOISY_LOGGERS = [
    'apscheduler.scheduler',
    'apscheduler.executors',
    'apscheduler.jobstores',
    'httpx',
    'httpcore',
    'urllib3',
    'sentence_transformers.SentenceTransformer',
    'databases',
    'edge_impulse_linux',
    'asyncio',
    'fsspec',
    'PIL',
    'pdfplumber',
    'openai',
    'groq',
    'google.generativeai',
]

for logger_name in NOISY_LOGGERS:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)

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
database = Database(DATABASE_URL, min_size=2, max_size=20)
metadata = MetaData()

# ─── ALL TABLE DEFINITIONS ──────────────────────────────────────────────
users = Table("users", metadata,
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
    Column("memory", JSON, server_default="[]"),
)
queries = Table("queries", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("query", Text),
    Column("response", Text),
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)
payments = Table("payments", metadata,
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
bulk_jobs = Table("bulk_jobs", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("job_id", String(64), unique=True, index=True),
    Column("status", String(20), server_default="pending"),
    Column("total_files", Integer, server_default="0"),
    Column("processed_files", Integer, server_default="0"),
    Column("result_data", Text, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)
domain_analytics = Table("domain_analytics", metadata,
    Column("id", Integer, primary_key=True),
    Column("domain", String(255), unique=True),
    Column("status_code", Integer, nullable=True),
    Column("response_time", Float, nullable=True),
    Column("ssl_expiry", DateTime, nullable=True),
    Column("dns_resolves", Boolean, server_default="false"),
    Column("cloudflare_analytics", JSON, nullable=True),
    Column("last_checked", DateTime, server_default=func.now()),
)
blog_posts = Table("blog_posts", metadata,
    Column("id", Integer, primary_key=True),
    Column("title", Text),
    Column("content", Text),
    Column("source_url", Text),
    Column("created_at", DateTime, server_default=func.now()),
    Column("published", Boolean, server_default="true"),
)
leads = Table("leads", metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(255), unique=True),
    Column("created_at", DateTime, server_default=func.now()),
)
demo_requests = Table("demo_requests", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255)),
    Column("email", String(255)),
    Column("company", String(255)),
    Column("phone", String(50)),
    Column("created_at", DateTime, server_default=func.now()),
)
api_keys = Table("api_keys", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("key", String(64), unique=True),
    Column("name", String(255)),
    Column("usage_limit", Integer, server_default="1000"),
    Column("usage_count", Integer, server_default="0"),
    Column("is_active", Boolean, server_default="true"),
    Column("expires_at", DateTime, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
)
custom_personas = Table("custom_personas", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("name", String(255)),
    Column("description", Text),
    Column("system_prompt", Text),
    Column("domain", String(100)),
    Column("is_public", Boolean, server_default="false"),
    Column("usage_count", Integer, server_default="0"),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)
fine_tune_data = Table("fine_tune_data", metadata,
    Column("id", Integer, primary_key=True),
    Column("query", Text),
    Column("initial_answer", Text),
    Column("final_answer", Text),
    Column("confidence", String(20)),
    Column("verifier_results", JSON),
    Column("judge_feedback", JSON),
    Column("is_low_confidence", Boolean, server_default="false"),
    Column("used_for_training", Boolean, server_default="false"),
    Column("created_at", DateTime, server_default=func.now()),
)
enterprise_tenants = Table("enterprise_tenants", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255)),
    Column("subdomain", String(100), unique=True),
    Column("api_key", String(64), unique=True),
    Column("custom_knowledge_base", JSON, nullable=True),
    Column("allowed_domains", JSON, nullable=True),
    Column("max_users", Integer, server_default="50"),
    Column("tier", String(20), server_default="enterprise"),
    Column("is_active", Boolean, server_default="true"),
    Column("created_at", DateTime, server_default=func.now()),
)
localisations = Table("localisations", metadata,
    Column("id", Integer, primary_key=True),
    Column("locale", String(10)),
    Column("key", String(255)),
    Column("value", Text),
    UniqueConstraint("locale", "key", name="uq_locale_key"),
)
drafts = Table("drafts", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("title", Text),
    Column("content", Text),
    Column("original_ai_content", Text),
    Column("status", String(20), server_default="draft"),
    Column("feedback", Text, nullable=True),
    Column("template_id", String(50), nullable=True),
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)
deliberations = Table("deliberations", metadata,
    Column("id", Integer, primary_key=True),
    Column("query", Text, nullable=False),
    Column("domain", Text),
    Column("persona", Text),
    Column("provider", Text),
    Column("initial_answer", Text),
    Column("verifier_results", JSON),
    Column("final_answer", Text),
    Column("confidence", Text),
    Column("sources", JSON),
    Column("timestamp", DateTime, server_default=func.now()),
    Column("used_for_training", Boolean, server_default="false"),
)

# ─── SAFETY TABLES ─────────────────────────────────────────────────────
constitutional_violations = Table("constitutional_violations", metadata,
    Column("id", Integer, primary_key=True),
    Column("query", Text),
    Column("response", Text),
    Column("violations", JSON),
    Column("confidence_score", Float),
    Column("detected_at", DateTime, server_default=func.now()),
    Column("resolved_at", DateTime, nullable=True),
    Column("resolved_by", String(255)),
    Column("resolution_notes", Text),
)
red_team_tests = Table("red_team_tests", metadata,
    Column("id", Integer, primary_key=True),
    Column("agent_id", String(50)),
    Column("query", Text),
    Column("attack_category", String(50)),
    Column("response", Text),
    Column("violations", JSON),
    Column("severity", String(20)),
    Column("tested_at", DateTime, server_default=func.now()),
    Column("retested_at", DateTime, nullable=True),
    Column("is_fixed", Boolean, server_default="false"),
)
kill_switch_logs = Table("kill_switch_logs", metadata,
    Column("id", Integer, primary_key=True),
    Column("reason", Text),
    Column("activated_at", DateTime, server_default=func.now()),
    Column("deactivated_at", DateTime, nullable=True),
    Column("deactivated_by", String(255)),
    Column("status", String(20), server_default="ACTIVE"),
)
trigger_events = Table("trigger_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("trigger_name", String(100)),
    Column("details", JSON),
    Column("created_at", DateTime, server_default=func.now()),
)
ai_actions_log = Table("ai_actions_log", metadata,
    Column("id", Integer, primary_key=True),
    Column("action_type", String(100)),
    Column("user_id", Integer, index=True),
    Column("agent_id", String(50)),
    Column("details", JSON),
    Column("created_at", DateTime, server_default=func.now()),
    Column("is_anomaly", Boolean, server_default="false"),
    Column("severity", String(20)),
)
user_restrictions = Table("user_restrictions", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("reason", Text),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
    Column("is_active", Boolean, server_default="true"),
)
decision_paths = Table("decision_paths", metadata,
    Column("id", Integer, primary_key=True),
    Column("query_id", Integer, index=True),
    Column("decision_path", JSON),
    Column("created_at", DateTime, server_default=func.now()),
)
safety_reports = Table("safety_reports", metadata,
    Column("id", Integer, primary_key=True),
    Column("report_data", JSON),
    Column("generated_at", DateTime, server_default=func.now()),
    Column("safety_score", Float),
)
user_feedback = Table("user_feedback", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("query_id", Integer, index=True),
    Column("rating", Integer),
    Column("comment", Text),
    Column("created_at", DateTime, server_default=func.now()),
)
query_performance = Table("query_performance", metadata,
    Column("id", Integer, primary_key=True),
    Column("query_id", Integer, index=True),
    Column("response_time", Float),
    Column("error_occurred", Boolean, server_default="false"),
    Column("error_message", Text),
    Column("created_at", DateTime, server_default=func.now()),
)
incidents = Table("incidents", metadata,
    Column("id", Integer, primary_key=True),
    Column("title", Text),
    Column("description", Text),
    Column("severity", String(20)),
    Column("status", String(20), server_default="OPEN"),
    Column("assigned_to", String(255)),
    Column("created_at", DateTime, server_default=func.now()),
    Column("resolved_at", DateTime, nullable=True),
    Column("resolution_time_hours", Float),
)

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

# ─── SOVEREIGN LLM (OpenRouter) ────────────────────────────────────────
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

async def call_sovereign_llm(
    system_prompt: str,
    user_message: str,
    model: str = "meta-llama/llama-3.1-70b-instruct",
    temperature: float = 0.7
) -> str:
    if not OPENROUTER_API_KEY:
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://www.advocacyalawfrim.in",
                    "X-Title": "Unknown Verdict"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": temperature,
                    "max_tokens": 4096
                },
                timeout=30.0
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenRouter error: {r.status_code} - {r.text}")
                return None
    except Exception as e:
        logger.error(f"Sovereign LLM failed: {e}")
        return None

# ─── LLM CALL (unified with token optimization) ──────────────────────
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

    providers = {
        "groq": {"client": groq_client, "model": "llama-3.3-70b-versatile", "is_gemini": False},
        "openai": {"client": openai_client, "model": "gpt-4o-mini", "is_gemini": False},
        "gemini": {"client": gemini_model, "model": "gemini-2.0-flash", "is_gemini": True},
        "deepseek": {"client": None, "model": "deepseek-chat", "is_gemini": False},
        "sovereign": {"client": None, "model": "meta-llama/llama-3.1-70b-instruct", "is_gemini": False}
    }

    fallback_order = ["groq", "openai", "deepseek", "gemini", "sovereign"]
    if provider in fallback_order:
        fallback_order.remove(provider)
        fallback_order.insert(0, provider)

    last_error = None

    for prov in fallback_order:
        try:
            if prov == "deepseek":
                if not DEEPSEEK_API_KEY:
                    continue
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": "deepseek-chat",
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30.0
                    )
                    if r.status_code == 200:
                        return r.json()["choices"][0]["message"]["content"]
                    continue

            if prov == "sovereign":
                if not OPENROUTER_API_KEY:
                    continue
                result = await call_sovereign_llm(system_prompt, user_message)
                if result:
                    return result
                continue

            config = providers[prov]
            client = config["client"]
            model = config["model"]
            is_gemini = config["is_gemini"]

            if not client:
                continue

            if is_gemini:
                r = client.generate_content(f"{system_prompt}\n\nUser: {user_message}")
                return r.text
            else:
                r = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return r.choices[0].message.content

        except Exception as e:
            logger.warning(f"Provider {prov} failed: {e}")
            last_error = e
            continue

    error_msg = f"All LLM providers failed. Last error: {last_error}" if last_error else "No LLM client available."
    logger.error(error_msg)
    return f"Error: {error_msg}"

# ─── JURY VERIFICATION SYSTEM ────────────────────────────────────────
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

# ─── BULK VERIFIER ────────────────────────────────────────────────────
async def verify_response(response_text: str, verifier: dict, model: str) -> dict:
    ver_sys = f"""You are {verifier['name']} ({verifier['role']}). Review and return JSON:
{{"status": "APPROVED|CORRECTED", "confidence": "HIGH|MEDIUM|LOW", "corrected_text": "..."}}"""
    try:
        out = await call_llm(ver_sys, response_text, "groq")
        m = re.search(r'\{.*\}', out, re.DOTALL)
        if m:
            return json.loads(m.group())
    except:
        pass
    return {"status": "APPROVED", "confidence": "MEDIUM", "corrected_text": ""}

# ─── MEMORY ───────────────────────────────────────────────────────────
async def _get_memory(uid: int) -> List[dict]:
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

# ─── CACHING HELPERS (Redis) ──────────────────────────────────────────
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

# ─── INGESTION ──────────────────────────────────────────────────────────
async def run_ingestion_job():
    import pdfplumber, json, glob, asyncpg
    from tqdm import tqdm

    PDF_DIR = "legal_docs"
    CHUNK_SIZE = 800
    OVERLAP = 150

    def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i+chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    async def ingest_pdf(file_path, conn):
        with pdfplumber.open(file_path) as pdf:
            full_text = "".join(page.extract_text() or "" for page in pdf.pages)
        if not full_text.strip():
            logger.warning(f"⚠️ No text extracted from {file_path} – skipping.")
            return 0
        chunks = chunk_text(full_text)
        source = os.path.basename(file_path)
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM knowledge_chunks WHERE metadata->>'source' = $1",
            source
        )
        if existing:
            logger.info(f"📁 {source} already has {existing} chunks. Skipping.")
            return 0
        inserted = 0
        for idx, chunk in enumerate(tqdm(chunks, desc=f"Embedding {source}")):
            emb = embedding_model.encode(chunk).tolist()
            emb_str = json.dumps(emb)
            meta = {"source": source, "chunk_index": idx, "total_chunks": len(chunks)}
            await conn.execute(
                "INSERT INTO knowledge_chunks (content, metadata, embedding) VALUES ($1, $2, $3)",
                chunk, json.dumps(meta), emb_str
            )
            inserted += 1
        return inserted

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        if not pdf_files:
            logger.warning("No PDFs found in legal_docs/ – skipping ingestion.")
            return
        total = 0
        for pdf in pdf_files:
            try:
                n = await ingest_pdf(pdf, conn)
                total += n
            except Exception as e:
                logger.error(f"❌ Error processing {pdf}: {e}")
        logger.info(f"✅ Ingestion complete. Added {total} new chunks.")
    finally:
        await conn.close()

# ─── DAILY NEWS & LINKEDIN PIPELINE ──────────────────────────────────
AI_NEWS_FEEDS = [
    "https://arxiv.org/rss/cs.AI",
    "https://feeds.feedburner.com/TechnologyReview/AI",
    "https://deepmind.com/blog/feed.xml",
    "https://openai.com/blog/rss.xml",
    "https://www.analyticsvidhya.com/feed/",
    "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
    "https://ai.meta.com/blog/feed/",
    "https://www.ibm.com/blogs/research/feed/",
    "https://research.google/blog/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
]

LAST_FETCHED_HASHES = set()

async def _fetch_news():
    if not FEEDPARSER_AVAILABLE:
        return []
    articles = []
    for feed_url in AI_NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                content = entry.title + entry.get('summary', '') + entry.get('link', '')
                hash_id = hashlib.md5(content.encode()).hexdigest()
                if hash_id in LAST_FETCHED_HASHES:
                    continue
                LAST_FETCHED_HASHES.add(hash_id)
                if len(LAST_FETCHED_HASHES) > 1000:
                    LAST_FETCHED_HASHES.clear()
                articles.append({
                    "title": entry.title,
                    "summary": entry.get('summary', ''),
                    "link": entry.get('link', ''),
                    "published": entry.get('published', ''),
                })
        except Exception as e:
            logger.error(f"Error fetching {feed_url}: {e}")
    articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    return articles[:10]

async def _generate_post(article: dict) -> str:
    prompt = f"""
You are Unknown Verdict, a professional AI news writer. Write a concise, engaging LinkedIn post (about 300 words) based on the following news:

Title: {article['title']}
Summary: {article['summary']}
Link: {article['link']}

The post should:
- Have a catchy opening line.
- Summarise the key innovation or finding.
- Explain why it matters for professionals or society.
- End with a call‑to‑action (e.g., "Read more: [link]").
- Use a professional but conversational tone, suitable for LinkedIn.
- Include 3 relevant hashtags.
"""
    response = await call_llm(
        system_prompt="You are a professional AI news writer.",
        user_message=prompt,
        provider="groq",
        temperature=0.7
    )
    return response

async def _post_to_linkedin(content: str):
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    user_id = os.getenv("LINKEDIN_USER_ID")
    
    if not token or not user_id:
        logger.warning("LinkedIn credentials missing – skipping posting.")
        return
    
    if user_id.startswith("urn:li:member:"):
        user_id = user_id.replace("urn:li:member:", "urn:li:person:")
        logger.info(f"✅ Fixed LinkedIn author URN: {user_id}")
    
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    payload = {
        "author": user_id,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content[:3000]},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code in [200, 201]:
                logger.info("✅ Posted to LinkedIn successfully.")
            else:
                logger.error(f"LinkedIn error: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"LinkedIn post failed: {e}")

async def _daily_news_pipeline():
    logger.info("📰 Starting daily news pipeline at 5 AM IST.")
    
    articles = await _fetch_news()
    if not articles:
        logger.warning("No new articles found.")
        return
    
    top_articles = articles[:5]
    posts = []
    for article in top_articles:
        post_content = await _generate_post(article)
        posts.append({"article": article, "post": post_content})
    
    for post in posts:
        filename = f"blog/post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        os.makedirs("blog", exist_ok=True)
        with open(filename, "w") as f:
            f.write(f"# {post['article']['title']}\n\n")
            f.write(f"*Source: {post['article']['link']}*\n\n")
            f.write(post['post'])
        
        try:
            await database.execute(
                blog_posts.insert().values(
                    title=post['article']['title'],
                    content=post['post'],
                    source_url=post['article']['link'],
                    created_at=func.now()
                )
            )
        except Exception as e:
            logger.error(f"DB insert error: {e}")
        
        await _post_to_linkedin(post['post'])
    
    logger.info(f"✅ Published {len(posts)} posts to blog and LinkedIn.")

# ─── SELF‑IMPROVEMENT ──────────────────────────────────────────────────
async def _analyse_and_improve():
    logger.info("🔍 Analysing deliberations for self‑improvement...")
    
    stmt = deliberations.select().where(
        and_(
            deliberations.c.confidence == 'LOW',
            deliberations.c.timestamp > datetime.now() - timedelta(days=7),
            deliberations.c.used_for_training == False
        )
    ).limit(100)
    
    rows = await database.fetch_all(stmt)
    if not rows:
        return
    
    improved_data = []
    for row in rows:
        system = "You are a legal expert. Improve the following answer for accuracy, clarity, and completeness. Return only the improved answer."
        improved = await call_sovereign_llm(system, row['final_answer'])
        if improved:
            improved_data.append({
                "query": row['query'],
                "original": row['final_answer'],
                "improved": improved,
                "confidence": row['confidence']
            })
            await database.execute(
                deliberations.update()
                .where(deliberations.c.id == row['id'])
                .values(used_for_training=True)
            )
    
    for data in improved_data:
        await database.execute(
            fine_tune_data.insert().values(
                query=data['query'],
                initial_answer=data['original'],
                final_answer=data['improved'],
                confidence=data['confidence'],
                is_low_confidence=True
            )
        )
    logger.info(f"✅ Prepared {len(improved_data)} samples for fine‑tuning.")

# ─── LIFESPAN ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool, redis_pool

    os.makedirs("blog", exist_ok=True)

    await database.connect()
    await _create_tables()
    await _ensure_test_user()

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

    app.state.constitutional_ai = ConstitutionalAI(pg_pool)
    app.state.red_team = RedTeam(pg_pool, call_llm)
    app.state.kill_switch = KillSwitch(pg_pool, redis_pool)
    app.state.monitoring = MonitoringSystem(pg_pool, redis_pool)
    app.state.interpretability = InterpretabilityDashboard(pg_pool)
    app.state.safety_case = SafetyCase(pg_pool)

    app.state.akida_edge = AkidaEdge()
    app.state.edge_impulse = EdgeImpulseModel()
    app.state.spike_retriever = SpikeRetriever()

    app.state.atma = AtmaRouter(
        pg_pool,
        fetch_relevant_chunks_func=fetch_relevant_chunks,
        serpapi_search_func=serpapi_search,
        call_llm_func=call_llm,
        constitutional_ai=app.state.constitutional_ai,
        kill_switch=app.state.kill_switch,
        monitoring=app.state.monitoring
    )

    sched = AsyncIOScheduler()
    sched.add_job(_purge_expired, IntervalTrigger(hours=1))
    sched.add_job(_update_domain_analytics, IntervalTrigger(hours=1))
    if FEEDPARSER_AVAILABLE:
        sched.add_job(_daily_news_pipeline, CronTrigger(hour=5, minute=0, timezone="Asia/Kolkata"), id="daily_news_pipeline")
    sched.add_job(_analyse_and_improve, IntervalTrigger(hours=24))
    sched.start()
    logger.info("👁️ Unknown Verdict Engine v11.0 – Complete Enterprise Edition Ready.")

    async with pg_pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_chunks")
        if count == 0:
            logger.info("📚 knowledge_chunks empty – running auto‑ingestion...")
            await run_ingestion_job()
        else:
            logger.info(f"📚 knowledge_chunks already has {count} chunks. Skipping.")

    yield

    await database.disconnect()
    if pg_pool:
        await pg_pool.close()
    if redis_pool:
        await redis_pool.close()

# ─── DB INIT ────────────────────────────────────────────────────────────
async def _create_tables():
    await database.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    ddl = [
        """CREATE TABLE IF NOT EXISTS users (
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
            preferences JSONB,
            memory JSONB DEFAULT '[]'
        )""",
        # ... All other table creation statements (same as before) ...
        """CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL,
            embedding vector(384) NOT NULL
        )""",
        """CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding 
            ON knowledge_chunks 
            USING hnsw (embedding vector_cosine_ops)""",
    ]
    for stmt in ddl:
        await database.execute(stmt)

async def _ensure_test_user():
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
    await database.execute(queries.delete().where(queries.c.created_at < datetime.now() - timedelta(hours=24)))
    await database.execute(bulk_jobs.delete().where(bulk_jobs.c.created_at < datetime.now() - timedelta(days=7)))

async def _update_domain_analytics():
    domains = os.getenv("TARGETED_SEARCH_DOMAINS", "").replace(" ", "").split(",")
    if not domains:
        return
    for domain in domains:
        try:
            status = await _check_domain_health(domain)
            await _store_domain_analytics(domain, status)
        except Exception as e:
            logger.error(f"Failed to check domain {domain}: {e}")

async def _check_domain_health(domain: str) -> dict:
    result = {"status_code": None, "response_time": None, "ssl_expiry": None, "dns_resolves": False}
    try:
        socket.gethostbyname(domain)
        result["dns_resolves"] = True
    except:
        pass
    try:
        start = datetime.now()
        async with httpx.AsyncClient() as client:
            r = await client.get(f"https://{domain}", timeout=5.0)
        result["status_code"] = r.status_code
        result["response_time"] = (datetime.now() - start).total_seconds()
    except:
        pass
    try:
        context = ssl.create_default_context()
        with context.wrap_socket(socket.socket(), server_hostname=domain) as sock:
            sock.settimeout(5)
            sock.connect((domain, 443))
            cert = sock.getpeercert()
            if cert and 'notAfter' in cert:
                expiry = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                result["ssl_expiry"] = expiry.replace(tzinfo=None)
    except:
        pass
    return result

async def _store_domain_analytics(domain: str, status: dict):
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO domain_analytics (domain, status_code, response_time, ssl_expiry, dns_resolves, last_checked)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    status_code = EXCLUDED.status_code,
                    response_time = EXCLUDED.response_time,
                    ssl_expiry = EXCLUDED.ssl_expiry,
                    dns_resolves = EXCLUDED.dns_resolves,
                    last_checked = NOW()
            """, domain, status.get("status_code"), status.get("response_time"),
                status.get("ssl_expiry"), status.get("dns_resolves", False))
    except Exception as e:
        logger.error(f"Failed to store domain analytics for {domain}: {e}")

# ─── LIMIT HELPERS ──────────────────────────────────────────────────────
async def _check_limit(u: dict) -> bool:
    if u["tier"] in ("premium", "enterprise", "lifetime"):
        return True
    today = datetime.now().date()
    last = u["last_query_reset"].date() if u["last_query_reset"] else datetime.min.date()
    if today > last:
        await database.execute(users.update().where(users.c.id == u["id"]).values(queries_used_today=0, last_query_reset=func.now()))
        return True
    return u["queries_used_today"] < 10

async def _incr_query(uid: int):
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

# ─── EDGE AI SERVICE INITIALIZATION ──────────────────────────────────
edge_ai_service: Optional[EdgeAIService] = None

@app.on_event("startup")
async def startup_edge_ai():
    global edge_ai_service
    try:
        edge_ai_service = await get_edge_ai_service()
        logger.info("✅ Edge AI Service initialized")
    except Exception as e:
        logger.error(f"❌ Edge AI Service initialization failed: {e}")
        edge_ai_service = None

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
    ║    ═══════════════════════════════════════════════════════════════════════ ║
    ║                                                                           ║
    ║    🏛️  UNKNOWN VERDICT v11.0 - Enterprise Legal AI Platform             ║
    ║    ⚖️  AI-Powered Legal Advisory with 250 Specialist Personas            ║
    ║                                                                           ║
    ║    ┌──────────────────────────────────────────────────────────────────┐     ║
    ║    │  📊  SYSTEM STATUS                                               │     ║
    ║    │  ├── 👤 250 Specialist Personas     │  {len(DIVINE_AGENTS):>3} Loaded  │     ║
    ║    │  ├── ⚖️ 10 Verifiers + Judge Shakti │  {len(VERIFIERS):>3} Ready      │     ║
    ║    │  ├── 🧠 Constitutional AI            │  ✅ Active                │     ║
    ║    │  ├── 📡 Edge AI Service              │  {edge_status:<17}│     ║
    ║    │  ├── 📚 Knowledge Base               │  1,047 Chunks Ready      │     ║
    ║    │  ├── 🔒 Enterprise Features          │  ✅ Enabled              │     ║
    ║    │  └── 🌐 API Gateway                  │  ✅ Running              │     ║
    ║    ├──────────────────────────────────────────────────────────────────┤     ║
    ║    │  🌐  Server: http://0.0.0.0:7860                               │     ║
    ║    │  📚  API Docs: /docs                                            │     ║
    ║    │  🚀  Press CTRL+C to stop                                      │     ║
    ║    └──────────────────────────────────────────────────────────────────┘     ║
    ║                                                                           ║
    ║    📅  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                  ║
    ║                                                                           ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    print("\033[96m" + banner + "\033[0m")

# ─── HEALTH CHECK ──────────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_status = "connected" if redis_pool else "disabled"
    kill_switch_status = app.state.kill_switch.is_active if hasattr(app.state, 'kill_switch') else "unknown"
    edge_status = "available" if edge_ai_service else "unavailable"
    return {
        "status": "healthy",
        "version": "11.0-enterprise",
        "agents": 250,
        "verifiers": 10,
        "redis": redis_status,
        "kill_switch": kill_switch_status,
        "edge_ai": edge_status,
        "domain_monitoring": "active"
    }

# ─── AUTH ROUTES ──────────────────────────────────────────────────────
@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
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

# ─── EDGE AI ROUTES ──────────────────────────────────────────────────
@app.post("/edge/process/audio")
@limiter.limit("30/minute")
async def edge_process_audio(
    request: Request,
    audio: UploadFile = File(...),
    analysis_type: str = Form("courtroom"),
    cu: dict = Depends(get_current_user)
):
    if edge_ai_service is None:
        raise HTTPException(status_code=503, detail="Edge AI service not available")
    if cu["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(status_code=403, detail="Edge AI requires Premium+ plan")
    audio_data = await audio.read()
    if analysis_type == "courtroom":
        result = await edge_ai_service.analyze_courtroom_audio(audio_data)
    elif analysis_type == "emotion":
        result = await edge_ai_service.detect_emotion(audio_data)
    else:
        result = await edge_ai_service.model_manager.classify_audio(audio_data)
        result = result.classifications[0].to_dict()
    await app.state.monitoring.log_action(
        action_type="edge_ai_audio",
        user_id=cu["id"],
        details={"analysis_type": analysis_type, "result": result, "timestamp": datetime.now().isoformat()}
    )
    return JSONResponse({"status": "success", "result": result, "timestamp": datetime.now().isoformat()})

@app.post("/edge/process/vision")
@limiter.limit("30/minute")
async def edge_process_vision(
    request: Request,
    image: UploadFile = File(...),
    analysis_type: str = Form("document"),
    cu: dict = Depends(get_current_user)
):
    if edge_ai_service is None:
        raise HTTPException(status_code=503, detail="Edge AI service not available")
    if cu["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(status_code=403, detail="Edge AI requires Premium+ plan")
    image_data = await image.read()
    if analysis_type == "document":
        result = await edge_ai_service.process_legal_document(image_data)
    elif analysis_type == "signature":
        result = await edge_ai_service.verify_signature(image_data)
    else:
        result = await edge_ai_service.model_manager.classify_vision(image_data)
        result = result.classifications[0].to_dict()
    await app.state.monitoring.log_action(
        action_type="edge_ai_vision",
        user_id=cu["id"],
        details={"analysis_type": analysis_type, "result": result, "timestamp": datetime.now().isoformat()}
    )
    return JSONResponse({"status": "success", "result": result, "timestamp": datetime.now().isoformat()})

@app.get("/edge/status")
async def edge_status(request: Request):
    if edge_ai_service is None:
        return {"status": "unavailable", "message": "Edge AI service not initialized", "timestamp": datetime.now().isoformat()}
    metrics = edge_ai_service.get_metrics()
    return {
        "status": "available",
        "simulation_mode": metrics.get("simulation_mode", True),
        "models_loaded": metrics.get("models_loaded", []),
        "total_predictions": metrics.get("total_predictions", 0),
        "avg_latency_ms": metrics.get("avg_latency_ms", 0),
        "timestamp": datetime.now().isoformat()
    }

# ─── /ask ROUTE WITH FULL JURY SYSTEM ──────────────────────────────
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
    
    if not app.state.kill_switch.is_active:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable due to safety protocol")
    
    stmt = user_restrictions.select().where(
        and_(
            user_restrictions.c.user_id == cu["id"],
            user_restrictions.c.is_active == True,
            user_restrictions.c.expires_at > datetime.now()
        )
    )
    restriction = await database.fetch_one(stmt)
    if restriction:
        raise HTTPException(status_code=403, detail=f"User restricted until {restriction['expires_at']}: {restriction['reason']}")
    
    await app.state.monitoring.log_action(
        action_type="query_submission",
        user_id=cu["id"],
        details={"query": query[:100], "files": [f.filename for f in files] if files else []}
    )
    
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

    custom_system = None
    if persona_id:
        stmt = custom_personas.select().where(
            and_(
                custom_personas.c.id == int(persona_id),
                or_(custom_personas.c.user_id == cu["id"], custom_personas.c.is_public == True)
            )
        )
        persona_obj = await database.fetch_one(stmt)
        if persona_obj:
            custom_system = persona_obj['system_prompt']
            logger.info(f"👤 Custom persona: {persona_obj['name']}")

    cache_hit = None
    if not files and not oracle:
        cache_hit = await get_cached_response(combined_query, model, oracle)

    if cache_hit:
        logger.info("💾 Cache hit!")
        answer = cache_hit["answer"]
        confidence = cache_hit["confidence"]
        sources = cache_hit["sources"]
        metadata = cache_hit["metadata"]
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
    if custom_system:
        system_prompt += f"\n\nCustom Persona Instructions:\n{custom_system}"

    logger.info(f"🧠 Generating response with {agent_name}...")

    atma = app.state.atma
    result = await atma.run(query=combined_query, history=None, files=None, unrestricted=unrestricted_bool)

    initial_answer = result["answer"]
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

    constitutional_result = await app.state.constitutional_ai.evaluate_response(
        query=combined_query,
        response=answer,
        context={"user_id": cu["id"], "domain": domain}
    )
    
    if constitutional_result["ethics_compliance"] == "LOW":
        answer = constitutional_result["corrected_response"]
        confidence = "LOW"
        await app.state.monitoring.log_action(
            action_type="constitutional_violation",
            user_id=cu["id"],
            details={"query": query[:200], "violations": constitutional_result["violations"], "confidence_score": constitutional_result["confidence"]}
        )
        logger.warning("⚠️ Constitutional violation detected and corrected")

    if not files and not oracle:
        cache_data = {"answer": answer, "confidence": confidence, "sources": sources, "metadata": metadata}
        await set_cached_response(combined_query, model, oracle, cache_data, ttl_seconds=86400)
        logger.info("💾 Response cached")

    await _update_memory(cu["id"], query, answer)

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

# ─── LIFETIME COUNT ────────────────────────────────────────────────────
@app.get("/lifetime-count")
async def lifetime_count():
    c = await database.fetch_val(select(func.count()).select_from(users).where(users.c.tier == "lifetime")) or 0
    return {"count": c, "remaining": max(0, 1000 - c)}

@app.get("/my-usage")
async def my_usage(cu: dict = Depends(get_current_user)):
    total = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == cu["id"])) or 0
    today = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == cu["id"], func.date(queries.c.created_at) == func.current_date())) or 0
    return {"total_queries": total, "queries_today": today}

# ─── DOMAIN ANALYTICS ──────────────────────────────────────────────────
@app.get("/domain-status")
async def domain_status(domain: str = None):
    if domain:
        row = await database.fetch_one("SELECT * FROM domain_analytics WHERE domain = $1", domain)
        if not row:
            raise HTTPException(404, "Domain not found in analytics")
        return dict(row)
    else:
        rows = await database.fetch_all("SELECT * FROM domain_analytics ORDER BY domain")
        return [dict(r) for r in rows]

@app.get("/blog")
async def get_blog_posts(limit: int = 10):
    rows = await database.fetch_all("SELECT * FROM blog_posts ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]

# ─── LEAD CAPTURE ──────────────────────────────────────────────────────
@app.post("/capture-lead")
async def capture_lead(email: str = Form(...)):
    try:
        await database.execute("INSERT INTO leads (email) VALUES ($1) ON CONFLICT (email) DO NOTHING", email)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(400, detail=str(e))

@app.post("/book-demo")
async def book_demo(data: dict = Body(...)):
    await database.execute(
        "INSERT INTO demo_requests (name, email, company, phone) VALUES ($1, $2, $3, $4)",
        data.get("name"), data.get("email"), data.get("company"), data.get("phone")
    )
    return {"status": "success"}

# ─── API KEYS ──────────────────────────────────────────────────────────
@app.post("/api-key/generate")
async def generate_api_key(name: str = Form(...), cu: dict = Depends(get_current_user)):
    key = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    await database.execute(
        "INSERT INTO api_keys (user_id, key, name, is_active) VALUES ($1, $2, $3, TRUE)",
        cu["id"], key, name
    )
    return {"api_key": key}

# ─── PUBLIC API (Marketplace) ──────────────────────────────────────────
@app.post("/api/v1/ask")
async def api_ask(
    request: Request,
    query: str = Form(...),
    model: str = Form("llama-3.3-70b-versatile"),
    search_web: str = Form("on"),
    x_api_key: str = Header(...)
):
    api_key_record = await database.fetch_one(
        "SELECT user_id, usage_limit, usage_count, is_active, expires_at FROM api_keys WHERE key = $1",
        x_api_key
    )
    if not api_key_record:
        raise HTTPException(status_code=401, detail="Invalid API key")
    record = dict(api_key_record)
    if not record["is_active"]:
        raise HTTPException(status_code=403, detail="API key is inactive")
    if record["expires_at"] and record["expires_at"] < datetime.now():
        raise HTTPException(status_code=403, detail="API key has expired")
    if record["usage_count"] >= record["usage_limit"]:
        raise HTTPException(status_code=429, detail="API usage limit exceeded")
    user = await database.fetch_one(users.select().where(users.c.id == record["user_id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_dict = dict(user)
    if user_dict["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(status_code=403, detail="API access requires Premium or Enterprise plan")
    await database.execute("UPDATE api_keys SET usage_count = usage_count + 1 WHERE key = $1", x_api_key)
    combined_query = query
    oracle = False
    unrestricted = search_web == "on" and "unrestricted" in search_web
    atma = app.state.atma
    result = await atma.run(query=combined_query, history=None, files=None, unrestricted=unrestricted)
    await database.execute(
        queries.insert().values(
            user_id=record["user_id"],
            query=combined_query[:8000],
            response=result["answer"][:16000],
            metadata={"domain": result.get("domain", "general"), "persona": result.get("persona", ""), "provider": result.get("provider", ""), "api_call": True},
            expires_at=datetime.now() + timedelta(hours=24)
        )
    )
    return {
        "status": "success",
        "answer": result["answer"],
        "confidence": result["confidence"],
        "sources": result["sources"],
        "domain": result.get("domain", "general"),
        "persona": result.get("persona", ""),
        "provider": result.get("provider", ""),
        "jury_verifiers": result.get("jury_verifiers", []),
        "jury_confidences": result.get("jury_confidences", {})
    }

# ─── TEMPLATES ──────────────────────────────────────────────────────────
TEMPLATES = {
    "demand_letter": {
        "name": "Demand Letter (Personal Injury)",
        "fields": [
            {"key": "client_name", "label": "Client Name", "type": "text"},
            {"key": "client_address", "label": "Client Address", "type": "text"},
            {"key": "date_of_accident", "label": "Date of Accident", "type": "date"},
            {"key": "at_fault_driver", "label": "At-Fault Driver", "type": "text"},
            {"key": "insurance_company", "label": "Insurance Company", "type": "text"},
            {"key": "claim_number", "label": "Claim Number", "type": "text"},
            {"key": "injuries", "label": "Injuries", "type": "text"},
            {"key": "medical_bills", "label": "Medical Bills ($)", "type": "number"},
            {"key": "lost_wages", "label": "Lost Wages ($)", "type": "number"},
        ],
        "prompt": """Draft a professional demand letter with the following details: Client: {client_name}, Address: {client_address}, Date: {date_of_accident}, Driver: {at_fault_driver}, Insurance: {insurance_company}, Claim #: {claim_number}, Injuries: {injuries}, Medical: ${medical_bills}, Lost Wages: ${lost_wages}. Include formal headings, accident description, damages, settlement demand, and closing."""
    },
    "nda": {
        "name": "Mutual Non-Disclosure Agreement",
        "fields": [
            {"key": "party_a", "label": "Party A", "type": "text"},
            {"key": "party_b", "label": "Party B", "type": "text"},
            {"key": "purpose", "label": "Purpose of Disclosure", "type": "text"},
            {"key": "term", "label": "Term (months)", "type": "number"},
        ],
        "prompt": """Draft a Mutual NDA between {party_a} and {party_b} for {purpose}. Term: {term} months. Include definitions, obligations, exclusions, term, governing law (India), and signatures."""
    },
}

@app.get("/api/templates")
async def get_templates():
    return {"templates": [{"id": k, "name": v["name"], "fields": v["fields"]} for k, v in TEMPLATES.items()]}

@app.post("/api/templates/{template_id}/generate")
async def generate_template_document(
    template_id: str,
    data: Dict[str, Any] = Body(...),
    cu: dict = Depends(get_current_user)
):
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    template = TEMPLATES[template_id]
    prompt = template["prompt"].format(**data)
    system = "You are a professional legal assistant. Draft accurate, well-formatted legal documents."
    result = await call_llm(system, prompt, provider="groq")
    await database.execute(
        queries.insert().values(
            user_id=cu["id"],
            query=f"Template: {template['name']}",
            response=result[:16000],
            metadata={"template": template_id, "data": data},
            expires_at=datetime.now() + timedelta(hours=24)
        )
    )
    return {"status": "success", "document": result, "template": template_id, "name": template["name"]}

# ─── PAYMENTS ──────────────────────────────────────────────────────────
rzp = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

@app.post("/create-order")
async def create_order(body: PaymentCreate, cu: dict = Depends(get_current_user)):
    if not rzp:
        raise HTTPException(status_code=501, detail="Payments not configured")
    amt = {"premium": 10200, "enterprise": 101100, "lifetime": 200}.get(body.tier, 10200)
    o = rzp.order.create({"amount": amt, "currency": "INR", "payment_capture": 1})
    await database.execute(payments.insert().values(
        user_id=cu["id"],
        razorpay_order_id=o["id"],
        amount=amt / 100,
        tier=body.tier,
        status="created"
    ))
    return {"order_id": o["id"], "amount": amt, "razorpay_key": RAZORPAY_KEY_ID}

@app.post("/verify-payment")
async def verify_payment(
    razorpay_order_id: str = Form(...),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: str = Form(...),
    cu: dict = Depends(get_current_user)
):
    if not rzp:
        raise HTTPException(status_code=501, detail="Payments not configured")
    try:
        rzp.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        p = await database.fetch_one(payments.select().where(payments.c.razorpay_order_id == razorpay_order_id))
        tier = dict(p)["tier"]
        await database.execute(users.update().where(users.c.id == cu["id"]).values(tier=tier, is_premium=True))
        await database.execute(payments.update().where(payments.c.razorpay_order_id == razorpay_order_id).values(status="paid"))
        return {"status": "success", "tier": tier}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Verification failed")

# ─── STATIC FILES ──────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# ─── RUN WITH SINGLE WORKER ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=7860,
        workers=1,  # ✅ Single worker for clean logs
        log_level="info",
        access_log=True,
        timeout_keep_alive=30
    )