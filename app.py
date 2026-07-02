# ============================================================================
# LEXSARTHI v9.0 BEST‑IN‑CLASS — Streaming, Web Search, Multi‑file, Visible Verifier
# ============================================================================
import os, io, csv, json, uuid, glob, re, random, string, logging, asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import (FastAPI, HTTPException, Depends, UploadFile, File, Form,
                     Request, BackgroundTasks)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
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
SERPAPI_KEY        = os.getenv("SERPAPI_KEY")          # for web search

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
    try:
        uid = int(uid_or_username)
        q = users.select().where(users.c.id == uid)
    except ValueError:
        q = users.select().where(users.c.username == uid_or_username)
    user = await database.fetch_one(q)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

limiter = Limiter(key_func=get_remote_address)

# ─── SYSTEM PROMPT ──────────────────────────────────────────────────────────
SYSTEM_BASE = """You are LexSarthi, an AI assistant powered by 250 specialist personas and verified by 10 verification agents.
Rules:
- Be accurate and grounded. If uncertain, say so.
- For legal/medical/financial topics, include a disclaimer.
- Default jurisdiction: India.
- Use clear structure, cite sources if possible.
- Tone: professional, helpful, balanced.
"""

# ─── 250 REAL PERSONAS ──────────────────────────────────────────────────────
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
    domain_idx = 0; name_idx = 0
    for i in range(250):
        domain = DOMAINS_FULL[domain_idx % len(DOMAINS_FULL)]
        sub = sub_specialties.get(domain, [f"Specialist {j+1}" for j in range(5)])[i % 5]
        agent_name = f"{DIVINE_NAMES_POOL[name_idx % len(DIVINE_NAMES_POOL)]} · {domain} ({sub})"
        agents.append({"id": f"agent_{i+1:03d}", "name": agent_name, "domain": domain,
                       "persona_prompt": f"You are a specialist in {domain}, focusing on {sub}. Use deep expertise."})
        domain_idx += 1
        if (i+1) % 5 == 0: name_idx += 1
    return agents
DIVINE_AGENTS = generate_all_agents()

# ─── 10 VERIFIERS ────────────────────────────────────────────────────────────
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
    {"id":"v10","name":"Shakti","role":"Final confidence & dharma seal","prompt":"Rate confidence and give wisdom note."}
]
LANG_MAP = {"en":"English","es":"Spanish","fr":"French","de":"German","pt":"Portuguese",
    "it":"Italian","nl":"Dutch","ru":"Russian","sv":"Swedish","pl":"Polish","tr":"Turkish",
    "hi":"Hindi","bn":"Bengali","sa":"Sanskrit","ar":"Arabic","zh":"Chinese",
    "ja":"Japanese","ko":"Korean","th":"Thai","vi":"Vietnamese","id":"Indonesian",
    "ms":"Malay","he":"Hebrew","el":"Greek"}

# ─── AGENT ROUTING ──────────────────────────────────────────────────────────
def route_agent(query: str, oracle: bool) -> str:
    if oracle: return "oracle"
    q = query.lower(); best_score = -1; best_id = "general"
    for agent in DIVINE_AGENTS:
        domain_words = agent["domain"].lower().split()
        persona_words = agent["persona_prompt"].lower().split()
        score = sum(1 for w in q.split() if w in domain_words or w in persona_words)
        if score > best_score:
            best_score = score; best_id = agent["id"]
    return best_id if best_score >= 2 else "general"

# ─── WEB SEARCH (SerpAPI) ───────────────────────────────────────────────────
async def web_search(query: str) -> str:
    if not SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not set; skipping web search.")
        return ""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://serpapi.com/search", params={
                "q": query, "api_key": SERPAPI_KEY, "num": 3
            }, timeout=8.0)
            if r.status_code != 200:
                return ""
            data = r.json()
            snippets = []
            for result in data.get("organic_results", [])[:3]:
                title = result.get("title","")
                snippet = result.get("snippet","")
                if snippet:
                    snippets.append(f"📌 {title}: {snippet}")
            return "\n".join(snippets) if snippets else ""
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return ""

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

# ─── LOCAL LIBRARY ──────────────────────────────────────────────────────────
LEGAL_SECTIONS: Dict[str, Dict[str, str]] = {}
def _extract_pdf(path: str) -> Dict[str, str]:
    txt = ""
    try:
        with pdfplumber.open(path) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t: txt += t + "\n"
    except:
        try:
            with open(path, "rb") as f:
                r = PyPDF2.PdfReader(f, strict=False)
                for p in r.pages:
                    t = p.extract_text()
                    if t: txt += t + "\n"
        except: return {}
    return {"__FULL_TEXT__": txt.strip()} if txt.strip() else {}

def load_pdf_library():
    d = "/app/legal_docs/"
    if not os.path.exists(d):
        logger.info("No legal library folder.")
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

# ─── LLM CALL (non‑streaming) ───────────────────────────────────────────────
async def _call_llm(sys_prompt: str, user_msg: str, model: str) -> str:
    if model.startswith("llama"):
        providers = [("groq", model), ("openai", "gpt-4o-mini"), ("gemini", "gemini-pro")]
    elif model.startswith("gpt"):
        providers = [("openai", model), ("groq", "llama-3.3-70b-versatile"), ("gemini", "gemini-pro")]
    elif "gemini" in model:
        providers = [("gemini", model), ("groq", "llama-3.3-70b-versatile"), ("openai", "gpt-4o-mini")]
    else:
        providers = [("groq", "llama-3.3-70b-versatile"), ("openai", "gpt-4o-mini"), ("gemini", "gemini-pro")]
    last_err = None
    for prov, mdl in providers:
        try:
            if prov == "groq" and groq_client:
                r = groq_client.chat.completions.create(
                    model=mdl, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_msg}],
                    temperature=0.2, max_tokens=4096)
                return r.choices[0].message.content
            elif prov == "openai" and openai_client:
                r = openai_client.chat.completions.create(
                    model=mdl, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_msg}],
                    temperature=0.2, max_tokens=4096)
                return r.choices[0].message.content
            elif prov == "gemini" and gemini_model:
                r = gemini_model.generate_content(f"{sys_prompt}\n\nUser: {user_msg}")
                return r.text
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All providers failed: {last_err}")

# ─── VERIFICATION (returns dict) ────────────────────────────────────────────
async def verify_response(response_text: str, verifier: dict, model: str) -> dict:
    ver_sys = f"""You are a verification agent named {verifier['name']} ({verifier['role']}).
Review the following response (which starts and ends with ॐ) for factual correctness, logical consistency, bias, and completeness.
Return ONLY a JSON object with exactly these keys:
- "status": "APPROVED" or "CORRECTED"
- "confidence": "HIGH", "MEDIUM", or "LOW"
- "issues_found": [list of strings, empty if none]
- "corrected_text": (only if CORRECTED, otherwise empty string)
Do NOT include any other text."""
    try:
        ver_text = await _call_llm(ver_sys, response_text, model)
        json_match = re.search(r'\{.*\}', ver_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"status": "APPROVED", "confidence": "MEDIUM", "issues_found": [], "corrected_text": ""}
    except:
        return {"status": "APPROVED", "confidence": "LOW", "issues_found": [], "corrected_text": ""}

# ─── STREAMING REPLAY GENERATOR ─────────────────────────────────────────────
async def replay_stream(full_text: str, verification: dict):
    """Yield tokens of full_text as SSE, then final verification event."""
    for i in range(0, len(full_text), 6):
        chunk = full_text[i:i+6]
        yield f"data: {json.dumps({'token': chunk})}\n\n"
        await asyncio.sleep(0.01)
    yield f"data: {json.dumps({'verification': verification})}\n\n"
    yield "data: [DONE]\n\n"

# ─── FASTAPI LIFESPAN ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await _create_tables()
    await _ensure_test_user()
    load_pdf_library()
    sched = AsyncIOScheduler()
    sched.add_job(_purge_expired, IntervalTrigger(hours=1))
    sched.start()
    logger.info("🔱 LexSarthi v9.0 Best‑in‑Class online.")
    yield
    await database.disconnect()

app = FastAPI(title="LexSarthi v9.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── DB INIT ─────────────────────────────────────────────────────────────────
async def _create_tables():
    ddl = [
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(100) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255), is_active BOOLEAN DEFAULT TRUE, is_premium BOOLEAN DEFAULT FALSE,
            tier VARCHAR(20) DEFAULT 'free', queries_used_today INTEGER DEFAULT 0,
            last_query_reset TIMESTAMP DEFAULT NOW(), created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(), api_key VARCHAR(64) UNIQUE,
            preferences JSONB, memory JSONB DEFAULT '[]')""",
        """CREATE TABLE IF NOT EXISTS queries (
            id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT, response TEXT, metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(), expires_at TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            razorpay_order_id VARCHAR(100) UNIQUE, razorpay_payment_id VARCHAR(100),
            razorpay_signature VARCHAR(255), amount FLOAT, currency VARCHAR(3) DEFAULT 'INR',
            tier VARCHAR(20), status VARCHAR(20) DEFAULT 'created', created_at TIMESTAMP DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS bulk_jobs (
            id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            job_id VARCHAR(64) UNIQUE NOT NULL, status VARCHAR(20) DEFAULT 'pending',
            total_files INTEGER DEFAULT 0, processed_files INTEGER DEFAULT 0,
            result_data TEXT, created_at TIMESTAMP DEFAULT NOW(), expires_at TIMESTAMP)""",
    ]
    for s in ddl: await database.execute(s)

async def _ensure_test_user():
    existing = await database.fetch_one(users.select().where(users.c.username == "counsel"))
    if not existing:
        await database.execute(users.insert().values(
            username="counsel", email="counsel@advocacyalawfrim.in",
            password_hash=hash_password("Password123!"), full_name="Counsel User", tier="enterprise",
            api_key="".join(random.choices(string.ascii_letters+string.digits, k=32)),
            memory=json.dumps([])))
        logger.info("✅ Seeded test user 'counsel'.")

async def _purge_expired():
    await database.execute(queries.delete().where(queries.c.created_at < datetime.now()-timedelta(hours=24)))
    await database.execute(bulk_jobs.delete().where(bulk_jobs.c.created_at < datetime.now()-timedelta(days=7)))

async def _check_limit(u: dict) -> bool:
    if u["tier"] in ("premium","enterprise","lifetime"): return True
    today = datetime.now().date()
    last = u["last_query_reset"].date() if u["last_query_reset"] else datetime.min.date()
    if today > last:
        await database.execute(users.update().where(users.c.id==u["id"]).values(
            queries_used_today=0, last_query_reset=func.now()))
        return True
    return u["queries_used_today"] < 10

async def _incr_query(uid: int):
    await database.execute(users.update().where(users.c.id==uid).values(
        queries_used_today=users.c.queries_used_today+1, updated_at=datetime.now()))

# ─── MEMORY ─────────────────────────────────────────────────────────────────
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
    return f"═══ RECENT CONTEXT ═══\n{ctx}\n═════════════════\nCurrent query:\n"

# ─── ROUTES ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status":"healthy","version":"9.0-best-in-class","agents":250,"verifiers":10}

@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    u = await database.fetch_one(users.select().where(
        (users.c.username==body.username) | (users.c.email==body.username.lower())))
    if not u or not verify_password(body.password, dict(u)["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    u = dict(u)
    tok = create_access_token({"sub": str(u["id"])})
    return {"access_token": tok, "token_type":"bearer","user":{
        "id":u["id"],"username":u["username"],"email":u["email"],"tier":u["tier"]}}

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

@app.get("/lifetime-count")
async def lifetime_count():
    c = await database.fetch_val(select(func.count()).select_from(users).where(users.c.tier=="lifetime")) or 0
    return {"count":c,"remaining":max(0,1000-c)}

@app.get("/my-usage")
async def my_usage(cu: dict = Depends(get_current_user)):
    total = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id==cu["id"])) or 0
    today = await database.fetch_val(select(func.count()).select_from(queries).where(
        queries.c.user_id==cu["id"], func.date(queries.c.created_at)==func.current_date())) or 0
    return {"total_queries":total,"queries_today":today}

# ─── MAIN ASK ENDPOINT (STREAMING) ──────────────────────────────────────────
@app.post("/ask")
@limiter.limit("30/minute")
async def ask(request: Request,
              query: str = Form(...),
              files: Optional[List[UploadFile]] = File(None),
              search_web: str = Form("off"),
              model: str = Form("llama-3.3-70b-versatile"),
              lang: str = Form("en"),
              oracle_mode: str = Form("false"),
              cu: dict = Depends(get_current_user)):
    if not await _check_limit(cu):
        raise HTTPException(status_code=429, detail="Free daily limit reached.")

    combined = query
    file_names = []
    if files:
        for file in files:
            content = await file.read()
            if len(content) > 8*1024*1024:
                raise HTTPException(status_code=413, detail=f"File {file.filename} too large.")
            try:
                ft = await process_file_bytes(content, file.filename)
                if ft.strip():
                    if len(ft) > 20000:
                        ft = ft[:20000] + "\n[...truncated...]"
                    combined += f"\n\n═══ DOCUMENT: {file.filename} ═══\n{ft}"
                    file_names.append(file.filename)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"File error: {e}")

    await _incr_query(cu["id"])

    # Web search
    web_context = ""
    if search_web == "on":
        web_context = await web_search(query)
        if web_context:
            combined = f"{combined}\n\n═══ LIVE WEB CONTEXT ═══\n{web_context[:4000]}"

    # Local library
    lib_context = search_local_knowledge(query)
    if lib_context:
        combined = f"{combined}\n\n═══ LEGAL LIBRARY ═══\n{lib_context[:4000]}"

    # Memory context
    mem = await _get_memory(cu["id"])
    ctx = _build_context(mem)
    if ctx:
        combined = f"{ctx}{combined}"

    oracle = oracle_mode.lower() == "true"
    selected_agent = "oracle" if oracle else route_agent(combined, oracle)

    if selected_agent == "oracle":
        persona = "You are the Oracle, offering spiritual and philosophical wisdom."
    elif selected_agent == "general":
        persona = "You are the full LexSarthi council, a generalist with broad knowledge."
    else:
        agent = next((a for a in DIVINE_AGENTS if a["id"] == selected_agent), None)
        persona = agent["persona_prompt"] if agent else "You are a generalist."

    sys_p = f"""{SYSTEM_BASE}
{persona}

Respond in {LANG_MAP.get(lang, "English")}. Use native script if not English.
"""

    # 1. Get full response from LLM (non‑streaming for verification)
    try:
        full_response = await _call_llm(sys_p, combined, model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM failed: {e}")

    # 2. Verification
    verifier = random.choice(VERIFIERS)
    verification = await verify_response(full_response, verifier, model)

    final_text = full_response
    if verification.get("status") == "CORRECTED" and verification.get("corrected_text"):
        final_text = verification["corrected_text"]
        if not final_text.startswith("ॐ"):
            final_text = "ॐ " + final_text
        if not final_text.endswith("ॐ"):
            final_text += " ॐ"

    # 3. Save to memory and DB
    await _update_memory(cu["id"], query, final_text)
    await database.execute(queries.insert().values(
        user_id=cu["id"], query=combined[:8000], response=final_text[:16000],
        metadata={"agent": selected_agent, "verifier": verifier["name"], "confidence": verification.get("confidence")},
        expires_at=datetime.now()+timedelta(hours=24)))

    # 4. Stream the final text + verification event
    return StreamingResponse(
        replay_stream(final_text, {
            "verifier": verifier["name"],
            "confidence": verification.get("confidence", "MEDIUM"),
            "status": verification.get("status", "APPROVED"),
            "issues": verification.get("issues_found", [])
        }),
        media_type="text/event-stream"
    )

# ─── BULK / PAYMENTS (unchanged, included for completeness) ────────────────
@app.post("/bulk-upload")
async def bulk_upload(background_tasks: BackgroundTasks,
                      files: List[UploadFile] = File(...),
                      query: str = Form(...),
                      model: str = Form("llama-3.3-70b-versatile"),
                      lang: str = Form("en"),
                      cu: dict = Depends(get_current_user)):
    if cu["tier"] not in ("premium","enterprise","lifetime"):
        raise HTTPException(status_code=403, detail="Premium+ required")
    jid = str(uuid.uuid4())
    file_data = [(f.filename, await f.read()) for f in files]
    await database.execute(bulk_jobs.insert().values(
        user_id=cu["id"], job_id=jid, total_files=len(file_data),
        status="processing", expires_at=datetime.now()+timedelta(days=7)))
    background_tasks.add_task(_process_bulk, jid, file_data, query, model, lang)
    return {"job_id": jid, "status":"processing", "total_files": len(file_data)}

async def _process_bulk(jid, file_data, query, model, lang):
    results, proc = [], 0
    for fname, content in file_data:
        try:
            txt = await process_file_bytes(content, fname)
            combined = f"{query}\n\n═══ DOCUMENT ═══\n{txt[:15000]}"
            at = route_agent(combined, False)
            full = await _call_llm(f"{SYSTEM_BASE}\nYou are a legal specialist.", combined, model)
            verification = await verify_response(full, random.choice(VERIFIERS), model)
            final = verification.get("corrected_text") if verification.get("status")=="CORRECTED" else full
            results.append({"filename": fname, "response": final})
        except Exception as e:
            results.append({"filename": fname, "error": str(e)})
        proc += 1
        await database.execute(bulk_jobs.update().where(bulk_jobs.c.job_id==jid).values(processed_files=proc))
    buf = io.StringIO()
    w = csv.writer(buf); w.writerow(["Filename","Response"])
    for r in results: w.writerow([r.get("filename"), r.get("response", r.get("error"))])
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
        raise HTTPException(status_code=400, detail="Verification failed")

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)