# ============================================================================
# LEXSARTHI v9.0 – UNIVERSAL DEFAULT OS  (FINAL)
# ============================================================================
# Owner   : THE ADVOCACY – A LAW FIRM
# Deploy  : upamnyu12-lex.hf.space
# Agents  : 250 Specialist Agents · 10 Verifiers
# Doctrine: Zero-Hallucination · Balanced Output · Correct Facts · Zero Retention
# Output  : ॐ ... [world‑class response] ... ॐ
# ============================================================================

import os, io, csv, json, uuid, glob, re, random, string, logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import (FastAPI, HTTPException, Depends, UploadFile, File, Form,
                     Request, BackgroundTasks)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import uvicorn

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from databases import Database
from sqlalchemy import (MetaData, Table, Column, Integer, String, DateTime,
                        Text, Boolean, JSON, Float, func, select)

import jwt
from passlib.context import CryptContext

import httpx
from groq import Groq
import openai
import google.generativeai as genai

import puremagic, PyPDF2, pdfplumber, docx
from PIL import Image
import pytesseract

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import razorpay

# ─── LOGGING ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("lexsarthi")

# ─── ENV ────────────────────────────────────────────────────────────────────
DATABASE_URL       = os.getenv("DATABASE_URL")
JWT_SECRET         = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ─── PROVIDER CLIENTS ───────────────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client   = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model  = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-pro")

# ─── DATABASE ───────────────────────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=2, max_size=20)
metadata = MetaData()

users = Table("users", metadata,
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
    Column("memory", JSON, server_default="[]"),
)
queries = Table("queries", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, index=True),
    Column("query", Text), Column("response", Text),
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)
payments = Table("payments", metadata,
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
bulk_jobs = Table("bulk_jobs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer),
    Column("job_id", String(64), unique=True, index=True),
    Column("status", String(20), server_default="pending"),
    Column("total_files", Integer, server_default="0"),
    Column("processed_files", Integer, server_default="0"),
    Column("result_data", Text, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)

# ─── PYDANTIC ───────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr; username: str; password: str; full_name: str
class UserLogin(BaseModel):
    username: str; password: str
class PaymentCreate(BaseModel):
    tier: str

# ─── SECURITY ───────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security    = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h):
    try: return pwd_context.verify(p, h)
    except: return False

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    try: return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except: raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(cred.credentials)
    uid_or_username = payload.get("sub")
    if not uid_or_username:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Try to interpret as integer (numeric user ID)
    try:
        uid = int(uid_or_username)
        query = users.select().where(users.c.id == uid)
    except ValueError:
        # If it's not an integer, treat it as username (for backward compatibility)
        username = uid_or_username
        query = users.select().where(users.c.username == username)

    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

limiter = Limiter(key_func=get_remote_address)

# ─── SYSTEM PROMPT (Removed deity references) ──────────────────────────────
SYSTEM_BASE = """You are LexSarthi — a universal intelligence Council with 250 specialist agents and 10 verifiers, operating under a doctrine of zero hallucination, balanced reasoning, and factual accuracy.

═ DOCTRINE (inviolable) ═
1. If uncertain about a fact, statute, or citation, say so explicitly. Never invent.
2. Weave together mathematics, logic, legal principle, scientific evidence, and philosophical/spiritual perspective where relevant — but label each clearly.
3. Cite sources wherever possible (Act + section, journal, scripture). If you cannot cite, state that.
4. Default jurisdiction: India (unless user specifies otherwise).
5. Structure responses with clear headings, bullet points, and short paragraphs for readability.
6. End every legal/medical/financial response with: "This is for informational purposes only, not professional advice."
7. Tone: professional, calm, precise, and authoritative.

═ AGENT ROSTER ═
You have access to specialists in: Constitutional, Contract, Criminal, Corporate, Tax, IP, Family, Cyber, Arbitration, Property, GST, Income Tax, Audit, Incorporation, Compliance, Mathematics, Statistics, Physics, Chemistry, Biology, Medicine, Psychology, Philosophy, Logic, Economics, Finance, History, Geopolitics, Astronomy, Vedanta, Yoga, Ayurveda, Sanskrit, Mythology, Ethics, AI Ethics, Cryptography, Blockchain, Climate Science, and more.

═══ RESPONSE STYLE (World-Class) ═══
- Provide depth: explain the "why", not just the "what".
- Include relevant examples or analogies where helpful.
- If answering a legal query, give step-by-step practical guidance.
- If answering a philosophical/spiritual query, offer insight with parables or metaphors.
- Always remain balanced and grounded in evidence.
- End every answer with a concise, actionable takeaway.
"""

def build_system_prompt(agent_persona: str, lang: str, oracle: bool) -> str:
    lang_name = LANG_MAP.get(lang, "English")
    lang_line = f"Respond in {lang_name}. Use the native script." if lang != "en" else ""
    if oracle:
        persona = "You are the Divine Oracle — offer wisdom, parable, and cosmic perspective; label clearly as SPIRITUAL INSIGHT (not empirical fact)."
    else:
        persona = agent_persona
    return f"{SYSTEM_BASE}\n{persona}\n\n{lang_line}"

# ─── OPENING / CLOSING (Single ॐ) ─────────────────────────────────────────
OPENING = "ॐ "
CLOSING = " ॐ"

# ─── AGENTS (250) ───────────────────────────────────────────────────────────
DIVINE_NAMES = ["Brahma","Vishnu","Shiva","Saraswati","Lakshmi","Ganesha","Hanuman",
    "Kartikeya","Indra","Yama","Surya","Chandra","Vayu","Agni","Varuna","Kubera",
    "Yamuna","Ganga","Durga","Kali","Tara","Bhuvaneshwari","Chinnamasta","Bhairavi",
    "Dhumavati","Bagalamukhi","Matangi","Kamala","Dattatreya","Narasimha","Vamana",
    "Parashurama","Rama","Krishna","Buddha","Kalki","Matsya","Kurma","Varaha","Skanda"]
DOMAINS = ["Constitutional Law","Contract Law","Criminal Law","Corporate Law","Tax Law",
    "IP Law","Family Law","Cyber Law","Arbitration","Property Law","GST","Income Tax",
    "Audit","Incorporation","Compliance","Mathematics","Statistics","Physics","Chemistry",
    "Biology","Medicine","Psychology","Philosophy","Logic","Reasoning","Economics",
    "Finance","History","Geopolitics","Astronomy","Vedanta","Yoga","Ayurveda","Sanskrit",
    "Mythology","Ethics","AI Ethics","Cryptography","Blockchain","Climate Science"]

def generate_divine_agents():
    agents = []
    for i in range(1, 251):
        n = DIVINE_NAMES[i % len(DIVINE_NAMES)]
        d = DOMAINS[i % len(DOMAINS)]
        agents.append({"id": f"agent_{i:03d}", "name": f"{n} · {d}", "domain": d})
    return agents
DIVINE_AGENTS = generate_divine_agents()

VERIFIERS = [
    {"id":"v01","name":"Ganesha","role":"Citation & logic integrity"},
    {"id":"v02","name":"Saraswati","role":"Knowledge cross-reference"},
    {"id":"v03","name":"Hanuman","role":"Global compliance"},
    {"id":"v04","name":"Kartikeya","role":"Contradiction detection"},
    {"id":"v05","name":"Indra","role":"Jurisdiction mapping"},
    {"id":"v06","name":"Yama","role":"Bias & neutrality"},
    {"id":"v07","name":"Surya","role":"Timeline & limitation"},
    {"id":"v08","name":"Chandra","role":"Precedent match"},
    {"id":"v09","name":"Vayu","role":"PII / privacy filter"},
    {"id":"v10","name":"Shakti","role":"Final confidence & dharma seal"},
]

LANG_MAP = {"en":"English","es":"Spanish","fr":"French","de":"German","pt":"Portuguese",
    "it":"Italian","nl":"Dutch","ru":"Russian","sv":"Swedish","pl":"Polish","tr":"Turkish",
    "hi":"Hindi","bn":"Bengali","sa":"Sanskrit","ar":"Arabic","zh":"Chinese",
    "ja":"Japanese","ko":"Korean","th":"Thai","vi":"Vietnamese","id":"Indonesian",
    "ms":"Malay","he":"Hebrew","el":"Greek"}

AGENT_PERSONAS = {
    "gst":          "You are Lord Kubera — specialist on Indian GST Act 2017: registration, returns (GSTR-1/3B/9), ITC, e-invoicing.",
    "income_tax":   "You are Goddess Lakshmi — specialist on Indian Income Tax Act 1961: ITR, TDS, capital gains, presumptive taxation.",
    "incorporation":"You are Lord Brahma — specialist on Companies Act 2013: incorporation of Pvt Ltd/OPC/LLP, MOA/AOA, ROC filings.",
    "firm":         "You are Lord Vishnu — specialist on Partnership Act 1932 and LLP Act 2008.",
    "audit":        "You are Lord Yama — specialist on statutory / tax / internal audit, ICAI standards, CARO 2020.",
    "contract":     "You are Lord Brahma — perform clause-by-clause contract review with: EXECUTIVE SUMMARY · RISK RATING · CLAUSE ANALYSIS · MISSING CLAUSES · RECOMMENDATIONS.",
    "research":     "You are Lord Hanuman — legal research: RELEVANT STATUTES · KEY CASE LAWS (with citation) · LEGAL PRINCIPLES.",
    "drafting":     "You are Goddess Saraswati — draft legal documents in professional Indian legal English.",
    "diligence":    "You are Lord Kartikeya — due diligence: COMPLIANCE STATUS · FINANCIAL RED FLAGS · LEGAL RISKS · REMEDIATION.",
    "about":        "You are LexSarthi itself. Introduce the platform: Universal Default OS, 250-agent council, zero-hallucination doctrine.",
    "general":      "You are the full Divine Council. Provide the most accurate, structured, jurisdiction-aware answer.",
}

def route_agent(q: str, oracle: bool) -> str:
    if oracle: return "oracle"
    ql = q.lower()
    if any(k in ql for k in ["who are you","what is lexsarthi","about lexsarthi"]): return "about"
    if any(k in ql for k in ["gst","gstr","goods and services tax","itc"]):          return "gst"
    if any(k in ql for k in ["income tax","itr","tds","capital gain"]):              return "income_tax"
    if any(k in ql for k in ["incorporate","pvt ltd","private limited","opc","moa","aoa"]): return "incorporation"
    if "llp" in ql or "partnership" in ql or "firm" in ql:                            return "firm"
    if "audit" in ql or "caro" in ql:                                                 return "audit"
    if "contract" in ql or "agreement" in ql or "review" in ql or "nda" in ql:       return "contract"
    if "case law" in ql or "judgment" in ql or "precedent" in ql or "research" in ql: return "research"
    if any(k in ql for k in ["draft","prepare","write me","create a"]):              return "drafting"
    if "due diligence" in ql or "compliance" in ql:                                  return "diligence"
    return "general"

# ─── LEGAL LIBRARY (LOCAL PDFs) ─────────────────────────────────────────────
LEGAL_SECTIONS: Dict[str, Dict[str, str]] = {}

def _extract_pdf(path: str) -> Dict[str, str]:
    txt = ""
    try:
        with pdfplumber.open(path) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t: txt += t + "\n"
    except Exception as e:
        logger.warning(f"pdfplumber failed on {path}: {e}")
        try:
            with open(path, "rb") as f:
                r = PyPDF2.PdfReader(f, strict=False)
                for p in r.pages:
                    t = p.extract_text()
                    if t: txt += t + "\n"
        except Exception as e2:
            logger.error(f"PyPDF2 also failed on {path}: {e2}")
            return {}
    return {"__FULL_TEXT__": txt.strip()} if txt.strip() else {}

def load_pdf_library():
    d = "/app/legal_docs/"
    if not os.path.exists(d):
        logger.info("No /app/legal_docs/ folder — running without local library.")
        return
    for fp in glob.glob(os.path.join(d, "*.pdf")):
        s = _extract_pdf(fp)
        if s:
            LEGAL_SECTIONS[os.path.basename(fp)] = s
    logger.info(f"✅ Legal library loaded: {len(LEGAL_SECTIONS)} PDFs")

def search_local_knowledge(query: str) -> str:
    if not LEGAL_SECTIONS: return ""
    kws = [w for w in query.lower().split() if len(w) > 3][:8]
    hits = []
    for fname, secs in LEGAL_SECTIONS.items():
        full = secs.get("__FULL_TEXT__", "")
        if not full: continue
        for line in full.split("\n"):
            if any(k in line.lower() for k in kws):
                hits.append(f"📜 **{fname[:-4]}**: {line.strip()}")
                if len(hits) >= 6: break
        if len(hits) >= 6: break
    return "\n".join(hits) if hits else ""

# ─── FILE PROCESSING ────────────────────────────────────────────────────────
async def process_file_bytes(content: bytes, filename: str) -> str:
    fn = filename.lower()
    try:
        if fn.endswith(".pdf"):
            text = ""
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for p in pdf.pages:
                    t = p.extract_text()
                    if t: text += t + "\n"
            if text.strip(): return text.strip()
            raise ValueError("PDF empty")
        if fn.endswith(".docx"):
            d = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in d.paragraphs).strip()
        if fn.endswith((".jpg",".jpeg",".png",".bmp",".tiff")):
            img = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(img).strip()
        return content.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        raise ValueError(f"Unable to read {filename}: {e}")

# ─── AI EXECUTION (MULTI-PROVIDER FALLBACK) ─────────────────────────────────
async def _call_groq(sys_p: str, user_q: str, model: str) -> str:
    if not groq_client: raise RuntimeError("Groq not configured")
    r = groq_client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":sys_p},{"role":"user","content":user_q}],
        temperature=0.2, max_tokens=4096)
    return r.choices[0].message.content

async def _call_openai(sys_p: str, user_q: str) -> str:
    if not openai_client: raise RuntimeError("OpenAI not configured")
    r = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":sys_p},{"role":"user","content":user_q}],
        temperature=0.2, max_tokens=4096)
    return r.choices[0].message.content

async def _call_gemini(sys_p: str, user_q: str) -> str:
    if not gemini_model: raise RuntimeError("Gemini not configured")
    r = gemini_model.generate_content(f"{sys_p}\n\nUser: {user_q}")
    return r.text

async def execute_ai(query: str, model: str, agent_type: str, lang: str,
                     oracle: bool) -> str:
    persona = AGENT_PERSONAS.get(agent_type, AGENT_PERSONAS["general"])
    sys_p   = build_system_prompt(persona, lang, oracle)

    library_ctx = search_local_knowledge(query)
    if library_ctx:
        sys_p += f"\n\n═══ LOCAL LIBRARY CONTEXT (authoritative) ═══\n{library_ctx[:4000]}"

    providers = []
    if model.startswith("llama"): providers = [("groq", model), ("openai", None), ("gemini", None)]
    elif model.startswith("gpt"): providers = [("openai", None), ("groq", "llama-3.3-70b-versatile"), ("gemini", None)]
    elif "gemini" in model:       providers = [("gemini", None), ("groq", "llama-3.3-70b-versatile"), ("openai", None)]
    else:                          providers = [("groq", "llama-3.3-70b-versatile"), ("openai", None), ("gemini", None)]

    last_err = None
    for prov, mdl in providers:
        try:
            if   prov == "groq":   out = await _call_groq(sys_p, query, mdl or "llama-3.3-70b-versatile")
            elif prov == "openai": out = await _call_openai(sys_p, query)
            elif prov == "gemini": out = await _call_gemini(sys_p, query)
            else: continue
            if out and out.strip():
                return f"{OPENING}{out.strip()}{CLOSING}"
        except Exception as e:
            last_err = e
            logger.warning(f"Provider {prov} failed: {e}")
            continue

    return f"{OPENING}I could not reach any AI provider at this moment. Please try again shortly.{CLOSING}"

# ─── LIFESPAN ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await _create_tables()
    await _ensure_test_user()
    load_pdf_library()
    sched = AsyncIOScheduler()
    sched.add_job(_purge_expired, IntervalTrigger(hours=1))
    sched.start()
    logger.info("🔱 LexSarthi v9.0 online — Zero Retention active.")
    yield
    await database.disconnect()

app = FastAPI(title="LexSarthi v9.0 — Universal Default OS", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── DB INIT ────────────────────────────────────────────────────────────────
async def _create_tables():
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
            memory JSONB DEFAULT '[]')""",
        """CREATE TABLE IF NOT EXISTS queries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT, response TEXT, metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(), expires_at TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            razorpay_order_id VARCHAR(100) UNIQUE,
            razorpay_payment_id VARCHAR(100),
            razorpay_signature VARCHAR(255),
            amount FLOAT, currency VARCHAR(3) DEFAULT 'INR',
            tier VARCHAR(20), status VARCHAR(20) DEFAULT 'created',
            created_at TIMESTAMP DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS bulk_jobs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            job_id VARCHAR(64) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            total_files INTEGER DEFAULT 0,
            processed_files INTEGER DEFAULT 0,
            result_data TEXT,
            created_at TIMESTAMP DEFAULT NOW(), expires_at TIMESTAMP)""",
    ]
    for s in ddl:
        await database.execute(s)

async def _ensure_test_user():
    existing = await database.fetch_one(users.select().where(users.c.username == "counsel"))
    if existing:
        logger.info("Test user 'counsel' already exists — preserved.")
        return
    await database.execute(users.insert().values(
        username="counsel", email="counsel@advocacyalawfrim.in",
        password_hash=hash_password("Password123!"),
        full_name="Counsel User", tier="enterprise",
        api_key="".join(random.choices(string.ascii_letters+string.digits, k=32)),
        memory=json.dumps([])))
    logger.info("✅ Seeded test user 'counsel' with Enterprise tier.")

async def _purge_expired():
    await database.execute(queries.delete().where(queries.c.created_at < datetime.now()-timedelta(hours=24)))
    await database.execute(bulk_jobs.delete().where(bulk_jobs.c.created_at < datetime.now()-timedelta(days=7)))
    logger.info("🔒 Zero-retention purge done.")

async def _check_limit(u: dict) -> bool:
    if u["tier"] in ("premium","enterprise","lifetime"): return True
    if datetime.now().date() > u["last_query_reset"].date(): return True
    return u["queries_used_today"] < 10

async def _incr_query(uid: int):
    await database.execute(users.update().where(users.c.id==uid).values(
        queries_used_today=users.c.queries_used_today+1, updated_at=datetime.now()))

async def _get_memory(uid: int) -> List[dict]:
    u = await database.fetch_one(users.select().where(users.c.id==uid))
    if not u: return []
    m = dict(u).get("memory") or []
    if isinstance(m, str):
        try: m = json.loads(m)
        except: m = []
    return m

async def _update_memory(uid: int, q: str, a: str):
    m = await _get_memory(uid)
    m.append({"q": q[:200], "a": a[:200]})
    m = m[-10:]
    await database.execute(users.update().where(users.c.id==uid).values(memory=json.dumps(m)))

def _build_context(mem: List[dict]) -> str:
    if not mem: return ""
    ctx = "\n".join(f"[Prev Q] {x['q']}\n[Prev A] {x['a']}" for x in mem[-3:])
    return f"═══ RECENT CONVERSATION CONTEXT ═══\n{ctx}\n═══════════════════════════\nCurrent query:\n"

# ─── ROUTES ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status":"healthy","version":"9.0","agents":len(DIVINE_AGENTS),
            "verifiers":len(VERIFIERS),"time":datetime.now().isoformat()}

@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    u = await database.fetch_one(users.select().where(users.c.username==body.username))
    if not u:
        u = await database.fetch_one(users.select().where(users.c.email==body.username.lower()))
    if not u or not verify_password(body.password, dict(u)["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    u = dict(u)
    tok = create_access_token({"sub": str(u["id"])})  # store numeric ID
    return {"access_token": tok, "token_type":"bearer","user":{
        "id":u["id"],"username":u["username"],"email":u["email"],
        "full_name":u["full_name"],"tier":u["tier"],"is_premium":u["is_premium"],
        "api_key":u.get("api_key")}}

@app.post("/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, body: UserCreate):
    ex = await database.fetch_one(users.select().where(
        (users.c.username==body.username)|(users.c.email==body.email.lower())))
    if ex: raise HTTPException(status_code=400, detail="User already exists")
    ak = "".join(random.choices(string.ascii_letters+string.digits, k=32))
    uid = await database.fetch_val(users.insert().values(
        username=body.username, email=body.email.lower(),
        password_hash=hash_password(body.password), full_name=body.full_name,
        tier="free", api_key=ak, memory=json.dumps([])).returning(users.c.id))
    tok = create_access_token({"sub": str(uid)})
    return {"access_token": tok, "token_type":"bearer","user":{"id":uid,"username":body.username,"api_key":ak}}

@app.get("/auth/me")
async def me(cu: dict = Depends(get_current_user)): return cu

@app.get("/agents-info")
async def agents_info():
    return {"total_agents":len(DIVINE_AGENTS),"total_verifiers":len(VERIFIERS),
            "sample_agents":DIVINE_AGENTS[:12],"verifiers":VERIFIERS}

@app.get("/lifetime-count")
async def lifetime_count():
    c = await database.fetch_val(select(func.count()).select_from(users).where(users.c.tier=="lifetime")) or 0
    return {"count":c,"limit":1000,"remaining":max(0,1000-c)}

@app.get("/my-usage")
async def my_usage(cu: dict = Depends(get_current_user)):
    total = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id==cu["id"])) or 0
    today = await database.fetch_val(select(func.count()).select_from(queries).where(
        queries.c.user_id==cu["id"], func.date(queries.c.created_at)==func.current_date())) or 0
    return {"total_queries":total,"queries_today":today}

@app.post("/ask")
@limiter.limit("30/minute")
async def ask(request: Request,
              query: str = Form(...),
              files: Optional[UploadFile] = File(None),
              search_web: str = Form("off"),
              model: str = Form("llama-3.3-70b-versatile"),
              agent_id: str = Form("agent_001"),
              lang: str = Form("en"),
              oracle_mode: str = Form("false"),
              cu: dict = Depends(get_current_user)):
    if not await _check_limit(cu):
        raise HTTPException(status_code=429, detail="Free daily limit reached. Upgrade for unlimited access.")

    combined = query
    has_file = False
    if files:
        has_file = True
        content = await files.read()
        if len(content) > 8*1024*1024:
            raise HTTPException(status_code=413, detail="File too large. Max 8MB. Use Bulk Upload for larger batches.")
        try:
            ft = await process_file_bytes(content, files.filename)
            if not ft or len(ft.strip()) < 20:
                raise HTTPException(status_code=400, detail="File contains no readable text.")
            if len(ft) > 20000:
                ft = ft[:20000] + "\n\n[...truncated for real-time processing — use Bulk Upload for full analysis...]"
            combined = f"{query}\n\n═══ DOCUMENT CONTENT ═══\n{ft}"
        except HTTPException: raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"File error: {e}")

    await _incr_query(cu["id"])

    mem = await _get_memory(cu["id"])
    ctx = _build_context(mem)
    if ctx: combined = ctx + combined

    oracle = oracle_mode.lower() == "true"
    at = route_agent(combined, oracle)

    resp = await execute_ai(combined, model, at, lang, oracle)
    await _update_memory(cu["id"], query, resp)

    await database.execute(queries.insert().values(
        user_id=cu["id"], query=combined[:8000], response=resp[:16000],
        metadata={"agent_type":at,"model":model,"has_file":has_file,"lang":lang,"oracle":oracle},
        expires_at=datetime.now()+timedelta(hours=24)))

    return {"response": resp, "model": model, "agent_used": at,
            "verified_by": [v["name"] for v in VERIFIERS], "council_size": 250}

# ─── BULK UPLOAD ────────────────────────────────────────────────────────────
@app.post("/bulk-upload")
async def bulk_upload(background_tasks: BackgroundTasks,
                      files: List[UploadFile] = File(...),
                      query: str = Form(...),
                      model: str = Form("llama-3.3-70b-versatile"),
                      lang: str = Form("en"),
                      cu: dict = Depends(get_current_user)):
    if cu["tier"] not in ("premium","enterprise","lifetime"):
        raise HTTPException(status_code=403, detail="Bulk upload requires Premium+")
    jid = str(uuid.uuid4())
    file_data = [(f.filename, await f.read()) for f in files]
    await database.execute(bulk_jobs.insert().values(
        user_id=cu["id"], job_id=jid, total_files=len(file_data),
        status="processing", expires_at=datetime.now()+timedelta(days=7)))
    background_tasks.add_task(_process_bulk, jid, file_data, query, model, lang)
    return {"job_id": jid, "status":"processing","total_files": len(file_data)}

async def _process_bulk(jid: str, file_data: list, query: str, model: str, lang: str):
    results, proc = [], 0
    for fname, content in file_data:
        try:
            txt = await process_file_bytes(content, fname)
            combined = f"{query}\n\n═══ DOCUMENT ═══\n{txt[:15000]}"
            at = route_agent(combined, False)
            r = await execute_ai(combined, model, at, lang, False)
            results.append({"filename": fname, "response": r})
        except Exception as e:
            results.append({"filename": fname, "error": str(e)})
        proc += 1
        await database.execute(bulk_jobs.update().where(bulk_jobs.c.job_id==jid).values(processed_files=proc))
    buf = io.StringIO()
    w = csv.writer(buf); w.writerow(["Filename","Response"])
    for r in results:
        w.writerow([r.get("filename"), r.get("response", r.get("error","Failed"))])
    await database.execute(bulk_jobs.update().where(bulk_jobs.c.job_id==jid).values(
        status="completed", result_data=buf.getvalue()))

@app.get("/bulk-result/{job_id}")
async def bulk_result(job_id: str, cu: dict = Depends(get_current_user)):
    j = await database.fetch_one(bulk_jobs.select().where(bulk_jobs.c.job_id==job_id))
    if not j: raise HTTPException(status_code=404, detail="Job not found")
    j = dict(j)
    if j["user_id"] != cu["id"]: raise HTTPException(status_code=403, detail="Access denied")
    if j["status"] != "completed":
        return {"status": j["status"], "processed": j["processed_files"], "total": j["total_files"]}
    return {"status":"completed","csv_data": j["result_data"]}

# ─── RAZORPAY ───────────────────────────────────────────────────────────────
rzp = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

@app.post("/create-order")
async def create_order(body: PaymentCreate, cu: dict = Depends(get_current_user)):
    if not rzp: raise HTTPException(status_code=501, detail="Payments not configured")
    amt = {"premium":10200,"enterprise":101100,"lifetime":200}.get(body.tier, 10200)
    o = rzp.order.create({"amount": amt, "currency":"INR","payment_capture":1})
    await database.execute(payments.insert().values(
        user_id=cu["id"], razorpay_order_id=o["id"], amount=amt/100,
        tier=body.tier, status="created"))
    return {"order_id": o["id"], "amount": amt, "razorpay_key": RAZORPAY_KEY_ID}

@app.post("/verify-payment")
async def verify_payment(razorpay_order_id: str = Form(...),
                          razorpay_payment_id: str = Form(...),
                          razorpay_signature: str = Form(...),
                          cu: dict = Depends(get_current_user)):
    if not rzp: raise HTTPException(status_code=501, detail="Payments not configured")
    try:
        rzp.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature})
        p = await database.fetch_one(payments.select().where(payments.c.razorpay_order_id==razorpay_order_id))
        tier = dict(p)["tier"]
        await database.execute(users.update().where(users.c.id==cu["id"]).values(tier=tier, is_premium=True))
        await database.execute(payments.update().where(payments.c.razorpay_order_id==razorpay_order_id).values(status="paid"))
        return {"status":"success","tier":tier}
    except Exception as e:
        logger.error(f"Payment verify failed: {e}")
        raise HTTPException(status_code=400, detail="Verification failed")

# ─── STATIC ──────────────────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)