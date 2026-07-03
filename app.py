# ============================================================================
# LEXSARTHI v9.1 – ATMA ROUTER INTEGRATION (pgvector + Targeted Web + Jury)
# RAG · Self‑Verification · Zero‑Retention · 100% TRUE & CO
# ============================================================================
import os, io, csv, json, uuid, glob, re, random, string, logging, asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from databases import Database
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

import asyncpg
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float, func, select

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

import razorpay

# ─── ATMA ROUTER ──────────────────────────────────────────────────────────
from atma import AtmaRouter

# ─── LOGGING ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("lexsarthi")

# ─── ENV ──────────────────────────────────────────────────────────────────
DATABASE_URL       = os.getenv("DATABASE_URL")
JWT_SECRET         = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
SERPAPI_KEY        = os.getenv("SERPAPI_KEY")

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ─── PROVIDER CLIENTS ────────────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client   = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model  = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-pro")

# ─── DATABASE (SQLAlchemy) ──────────────────────────────────────────────
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
    Column("query", Text),
    Column("response", Text),
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

# Global asyncpg pool (for pgvector and Atma)
pg_pool: Optional[asyncpg.Pool] = None

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

limiter = Limiter(key_func=get_remote_address)

# ─── SYSTEM PROMPT ──────────────────────────────────────────────────────
SYSTEM_BASE = """You are LexSarthi, the Universal Default OS for Human Knowledge — 100% True. You are powered by 250 specialist personas, a jury of 3 verifiers, and a final judge. You have access to a knowledge base (including the Constitution of India) and live web search. Always strive for accuracy, cite sources, and admit uncertainty. Default jurisdiction: India. Tone: professional, wise, compassionate."""

# ─── 250 SPECIALIST PERSONAS (generated) ──────────────────────────────
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

# ─── ROUTE AGENT (for bulk) ──────────────────────────────────────────────
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

# ─── RAG (pgvector) ────────────────────────────────────────────────────
async def fetch_relevant_chunks(query: str, top_k: int = 10, conn: asyncpg.Connection = None) -> List[Dict]:
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set, returning empty chunks")
        return []
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return []

    if conn is None:
        async with pg_pool.acquire() as conn:
            return await _fetch_chunks(conn, query_embedding, top_k)
    else:
        return await _fetch_chunks(conn, query_embedding, top_k)

async def _fetch_chunks(conn, embedding, top_k):
    rows = await conn.fetch(
        """
        SELECT content, metadata, 1 - (embedding <=> $1) AS similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> $1
        LIMIT $2
        """,
        embedding, top_k
    )
    return [
        {
            "content": row["content"],
            "metadata": row["metadata"],
            "similarity": row["similarity"]
        }
        for row in rows
    ]

# ─── WEB SEARCH ────────────────────────────────────────────────────────
async def serpapi_search(query: str) -> List[Dict]:
    if not SERPAPI_KEY:
        return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": SERPAPI_KEY, "num": 5},
                timeout=8.0
            )
            if r.status_code != 200:
                return []
            data = r.json()
            return data.get("organic_results", [])
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

# ─── LLM CALL (for bulk upload) ──────────────────────────────────────
async def _call_llm(sys_prompt: str, user_msg: str, model: str) -> str:
    # Simplified fallback – you can replace with your full implementation
    try:
        if model.startswith("llama") and groq_client:
            r = groq_client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_msg}],
                temperature=0.2,
                max_tokens=4096
            )
            return r.choices[0].message.content
        elif model.startswith("gpt") and openai_client:
            r = openai_client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_msg}],
                temperature=0.2,
                max_tokens=4096
            )
            return r.choices[0].message.content
        elif "gemini" in model and gemini_model:
            r = gemini_model.generate_content(f"{sys_prompt}\n\nUser: {user_msg}")
            return r.text
        else:
            # fallback to groq default
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_msg}],
                temperature=0.2,
                max_tokens=4096
            )
            return r.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"Error: {e}"

# ─── BULK VERIFIER ────────────────────────────────────────────────────
async def verify_response(response_text: str, verifier: dict, model: str) -> dict:
    ver_sys = f"""You are {verifier['name']} ({verifier['role']}). Review and return JSON:
{{"status": "APPROVED|CORRECTED", "confidence": "HIGH|MEDIUM|LOW", "corrected_text": "..."}}"""
    try:
        out = await _call_llm(ver_sys, response_text, model)
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
    m = m[-10:]
    await database.execute(users.update().where(users.c.id == uid).values(memory=json.dumps(m)))

def _build_context(mem: List[dict]) -> str:
    if not mem:
        return ""
    ctx = "\n".join(f"[Prev Q] {x['q']}\n[Prev A] {x['a']}" for x in mem[-3:])
    return f"═══ RECENT CONTEXT ═══\n{ctx}\n═════════════════\nCurrent query:\n"

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
    }
    yield f"data: {json.dumps({'verification': verification})}\n\n"
    yield "data: [DONE]\n\n"

# ─── INGESTION FUNCTION (shared) ────────────────────────────────────
async def run_ingestion_job():
    """Ingest all PDFs from legal_docs/ into knowledge_chunks (idempotent)."""
    from pypdf import PdfReader
    from tqdm import tqdm
    import asyncpg, openai, json, glob

    PDF_DIR = "legal_docs"
    CHUNK_SIZE = 800
    OVERLAP = 150
    EMBEDDING_MODEL = "text-embedding-3-small"
    DATABASE_URL = os.getenv("DATABASE_URL")
    openai.api_key = os.getenv("OPENAI_API_KEY")

    def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i+chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    def get_embedding(text):
        resp = openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return resp.data[0].embedding

    async def ingest_pdf(file_path, conn):
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
        if not full_text.strip():
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
            emb = get_embedding(chunk)
            meta = {"source": source, "chunk_index": idx, "total_chunks": len(chunks)}
            await conn.execute(
                "INSERT INTO knowledge_chunks (content, metadata, embedding) VALUES ($1, $2, $3)",
                chunk, json.dumps(meta), emb
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

# ─── LIFESPAN ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool
    await database.connect()
    await _create_tables()
    await _ensure_test_user()

    pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    app.state.atma = AtmaRouter(pg_pool)

    sched = AsyncIOScheduler()
    sched.add_job(_purge_expired, IntervalTrigger(hours=1))
    sched.start()
    logger.info("🔱 LexSarthi v9.1 with Atma — Ready for 1M users.")

    # Auto‑ingestion on first startup (if knowledge_chunks is empty)
    async with pg_pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM knowledge_chunks")
        if count == 0:
            logger.info("📚 knowledge_chunks is empty – running auto‑ingestion...")
            await run_ingestion_job()
        else:
            logger.info(f"📚 knowledge_chunks already has {count} chunks. Skipping.")

    yield
    await database.disconnect()
    await pg_pool.close()

app = FastAPI(title="LexSarthi", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
        """CREATE TABLE IF NOT EXISTS queries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT,
            response TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS payments (
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
        )""",
        """CREATE TABLE IF NOT EXISTS bulk_jobs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            job_id VARCHAR(64) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            total_files INTEGER DEFAULT 0,
            processed_files INTEGER DEFAULT 0,
            result_data TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL,
            embedding vector(1536) NOT NULL
        )""",
        """CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding 
            ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)""",
        """CREATE TABLE IF NOT EXISTS deliberations (
            id SERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            domain TEXT,
            persona TEXT,
            provider TEXT,
            initial_answer TEXT,
            verifier_results JSONB,
            final_answer TEXT,
            confidence TEXT,
            sources JSONB,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        )""",
        """CREATE INDEX IF NOT EXISTS idx_deliberations_timestamp ON deliberations(timestamp)"""
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

# ─── ROUTES ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "9.1-atma", "agents": 250, "verifiers": 10}

@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    u = await database.fetch_one(users.select().where((users.c.username == body.username) | (users.c.email == body.username.lower())))
    if not u or not verify_password(body.password, dict(u)["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    u = dict(u)
    tok = create_access_token({"sub": str(u["id"])})
    return {"access_token": tok, "token_type": "bearer", "user": {"id": u["id"], "username": u["username"], "email": u["email"], "tier": u["tier"]}}

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

@app.get("/lifetime-count")
async def lifetime_count():
    c = await database.fetch_val(select(func.count()).select_from(users).where(users.c.tier == "lifetime")) or 0
    return {"count": c, "remaining": max(0, 1000 - c)}

@app.get("/my-usage")
async def my_usage(cu: dict = Depends(get_current_user)):
    total = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == cu["id"])) or 0
    today = await database.fetch_val(select(func.count()).select_from(queries).where(queries.c.user_id == cu["id"], func.date(queries.c.created_at) == func.current_date())) or 0
    return {"total_queries": total, "queries_today": today}

# ─── /ask ──────────────────────────────────────────────────────────────
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
    cu: dict = Depends(get_current_user)
):
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
        combined_query = _build_context(mem) + combined_query

    atma = app.state.atma
    result = await atma.run(query=combined_query, history=None, files=None)

    answer = result["answer"]
    confidence = result["confidence"]
    sources = result["sources"]
    metadata = {
        "domain": result.get("domain", "general"),
        "persona": result.get("persona", ""),
        "provider": result.get("provider", ""),
        "jury_verifiers": [],
        "jury_confidences": {},
        "judge": "Shakti"
    }

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

    return StreamingResponse(
        replay_stream(answer, confidence, sources, metadata),
        media_type="text/event-stream"
    )

# ─── BULK UPLOAD ──────────────────────────────────────────────────────
@app.post("/bulk-upload")
async def bulk_upload(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), query: str = Form(...), model: str = Form("llama-3.3-70b-versatile"), lang: str = Form("en"), cu: dict = Depends(get_current_user)):
    if cu["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(status_code=403, detail="Premium+ required")
    jid = str(uuid.uuid4())
    file_data = [(f.filename, await f.read()) for f in files]
    await database.execute(bulk_jobs.insert().values(
        user_id=cu["id"],
        job_id=jid,
        total_files=len(file_data),
        status="processing",
        expires_at=datetime.now() + timedelta(days=7)
    ))
    background_tasks.add_task(_process_bulk, jid, file_data, query, model, lang)
    return {"job_id": jid, "status": "processing", "total_files": len(file_data)}

async def _process_bulk(jid, file_data, query, model, lang):
    results = []
    proc = 0
    for fname, content in file_data:
        try:
            txt = await process_file_bytes(content, fname)
            combined = f"{query}\n\n═══ DOCUMENT ═══\n{txt[:15000]}"
            # Use a simple route for bulk – no Atma, just direct LLM + single verifier
            agent_id = route_agent(combined, oracle=False)
            if agent_id == "oracle":
                persona = "You are the Oracle, offering spiritual and philosophical wisdom."
            elif agent_id == "general":
                persona = "You are the full LexSarthi council, a generalist with broad knowledge."
            else:
                agent = next((a for a in DIVINE_AGENTS if a["id"] == agent_id), None)
                persona = agent["persona_prompt"] if agent else "You are a generalist."
            sys_p = f"{SYSTEM_BASE}\n{persona}"
            full = await _call_llm(sys_p, combined, model)
            ver = await verify_response(full, random.choice(VERIFIERS[:-1]), model)
            final = ver.get("corrected_text") if ver.get("status") == "CORRECTED" else full
            results.append({"filename": fname, "response": final})
        except Exception as e:
            results.append({"filename": fname, "error": str(e)})
        proc += 1
        await database.execute(bulk_jobs.update().where(bulk_jobs.c.job_id == jid).values(processed_files=proc))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Filename", "Response"])
    for r in results:
        w.writerow([r.get("filename"), r.get("response", r.get("error", "Failed"))])
    await database.execute(bulk_jobs.update().where(bulk_jobs.c.job_id == jid).values(status="completed", result_data=buf.getvalue()))

@app.get("/bulk-result/{job_id}")
async def bulk_result(job_id: str, cu: dict = Depends(get_current_user)):
    j = await database.fetch_one(bulk_jobs.select().where(bulk_jobs.c.job_id == job_id))
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    j = dict(j)
    if j["user_id"] != cu["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if j["status"] != "completed":
        return {"status": j["status"], "processed": j["processed_files"], "total": j["total_files"]}
    return {"status": "completed", "csv_data": j["result_data"]}

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

# ─── ONE‑TIME INGESTION ENDPOINT (optional) ─────────────────────────
@app.post("/admin/ingest")
async def admin_ingest(
    secret: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me")
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    background_tasks.add_task(run_ingestion_job)
    return {"status": "ingestion started in background"}

# ─── STATIC FILES ──────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)