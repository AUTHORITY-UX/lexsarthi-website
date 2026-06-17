# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os
import json
import io
import hashlib
import re
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Literal, Callable, Awaitable
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import PyPDF2
import pdfplumber
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
import razorpay

# Try to import Google OAuth – if not installed, fall back to standard SMTP
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("Google OAuth not available – email will use standard SMTP (if configured)")

app = FastAPI(title="LexSarthi API", version="3.0")

# ========== CORS – ALLOW YOUR FRONTEND DOMAINS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://advocacyalawfrim.in",
        "https://www.advocacyalawfrim.in",
        "https://advocacyalawfirm.in",
        "https://www.advocacyalawfirm.in",
        "https://lexsarthi-website.pages.dev",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# SCHEMAS
# ========================
class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class HistoryItem(BaseModel):
    id: int
    agent: str
    input_summary: Optional[str]
    result_json: dict
    created_at: datetime

class ClauseReview(BaseModel):
    clause_number: str
    clause_text: str
    risk: Literal["Low", "Medium", "High", "Critical"]
    summary: str
    suggested_change: str
    actionable: bool
    reason: str

class DomainReviewResponse(BaseModel):
    agreement_type: str
    overall_risk: Literal["Low", "Medium", "High"]
    executive_summary: str
    clauses: List[ClauseReview]
    lawyer_review_required: bool
    review_id: Optional[str] = None

# ---------- Configuration ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")
client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
MODEL = "meta-llama/llama-3.1-8b-instruct"
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# ---------- Razorpay ----------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError("Razorpay keys not set")
rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ---------- Database ----------
SQLALCHEMY_DATABASE_URL = "sqlite:///./lexsarthi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    history = relationship("History", back_populates="user")

class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent = Column(String)
    input_summary = Column(String, nullable=True)
    result_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="history")

class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ---------- Auth (using PBKDF2 to avoid bcrypt 72-byte limit) ----------
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)
def get_password_hash(password):
    return pwd_context.hash(password)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user_optional(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        db.close()
        return user
    except:
        return None

# ---------- Utilities ----------
def extract_json_from_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except:
        match = re.search(r'\{.*\}(?=\s*$|\s*\{)', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return {"error": "Could not parse JSON", "raw": text[:200]}

async def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except:
        pass
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except:
        pass
    return ""

# ---------- LLM Caller ----------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def call_llm(system: str, user: str, json_mode: bool = True) -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content

# ---------- Cache ----------
cache = {}
CACHE_TTL = 300
def get_cache_key(text: str, agent: str) -> str:
    return f"{agent}:{hashlib.md5(text.encode()).hexdigest()}"
def get_cached_response(key: str) -> Optional[dict]:
    if key in cache and (datetime.utcnow() - cache[key]["timestamp"]).seconds < CACHE_TTL:
        return cache[key]["data"]
    return None
def set_cached_response(key: str, data: dict):
    cache[key] = {"data": data, "timestamp": datetime.utcnow()}

# ---------- Lawyer Review ----------
LAWYER_REVIEW = {
    "reviewed_by": "Adv. Pankaj Rustagi",
    "experience": "40 years in corporate law, IBC, RERA, due diligence.",
    "areas": ["IBC", "RERA", "Due Diligence", "Contract Negotiation", "Legal Research"],
    "qualification": "LLB, Campus Law Centre, Delhi University",
    "note": "AI-generated analysis reviewed by an advocate. For final legal advice, consult."
}
def add_lawyer_review(response: dict, flag: bool) -> dict:
    if flag:
        response["lawyer_review"] = {**LAWYER_REVIEW, "review_date": datetime.utcnow().isoformat()}
    return response

# ---------- Save History ----------
async def save_history_if_user(user: Optional[User], agent: str, input_text: str, result: dict):
    if user:
        db = SessionLocal()
        history = History(
            user_id=user.id,
            agent=agent,
            input_summary=input_text[:100] + ("..." if len(input_text)>100 else ""),
            result_json=json.dumps(result)
        )
        db.add(history)
        db.commit()
        db.close()

# ========================
# AGENT REGISTRY
# ========================
AgentHandler = Callable[[str], Awaitable[dict]]
AGENT_REGISTRY: Dict[str, AgentHandler] = {}

def register_agent(name: str):
    def decorator(func: AgentHandler):
        AGENT_REGISTRY[name] = func
        return func
    return decorator

# ========================
# AGENT DEFINITIONS – All 16 (copy your existing ones here)
# ========================
# (Placeholder – you already have all the agent functions; keep them unchanged)
# I'll include one example:
@register_agent("contract_risk")
async def analyze_contract_risk(text: str) -> dict:
    # ... your full prompt and logic ...
    pass

# ... repeat for all other agents (dpdp_check, legal_notice, etc.)

# ========================
# AUTH ENDPOINTS
# ========================
@app.post("/signup", response_model=Token)
async def signup(user: UserCreate):
    try:
        db = SessionLocal()
        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            db.close()
            raise HTTPException(400, "Email already registered")
        hashed = get_password_hash(user.password)
        new_user = User(email=user.email, hashed_password=hashed)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.email == form_data.username).first()
    db.close()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/history", response_model=List[HistoryItem])
async def get_history(current_user: User = Depends(get_current_user_optional)):
    if not current_user:
        raise HTTPException(401, "Authentication required")
    db = SessionLocal()
    history = db.query(History).filter(History.user_id == current_user.id).order_by(History.created_at.desc()).all()
    db.close()
    return [HistoryItem(
        id=h.id,
        agent=h.agent,
        input_summary=h.input_summary,
        result_json=json.loads(h.result_json),
        created_at=h.created_at
    ) for h in history]

# ========================
# CONTACT FORM – with OAuth fallback
# ========================
def get_gmail_access_token():
    if not GOOGLE_AVAILABLE:
        return None
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    creds.refresh(Request())
    return creds.token

def send_email_notification(name: str, email: str, subject: str, message: str):
    gmail_user = os.getenv("GMAIL_EMAIL")
    if not gmail_user:
        print("GMAIL_EMAIL not set")
        return

    recipients = ["upmanyu.du@gmail.com", "advocacy@advocacyalawfrim.in"]

    # Try OAuth first if available
    access_token = None
    if GOOGLE_AVAILABLE:
        try:
            access_token = get_gmail_access_token()
        except Exception as e:
            print(f"OAuth token error: {e}")

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = f"New Lead: {subject}"
    body = f"New contact form submission:\n\nName: {name}\nEmail: {email}\nSubject: {subject}\nMessage: {message}\n\nConsent given: Yes\nTimestamp: {datetime.utcnow().isoformat()}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        if access_token:
            # Use XOAUTH2
            auth_string = f"user={gmail_user}\x01auth=Bearer {access_token}\x01\x01"
            auth_bs64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            code, _ = server.docmd("AUTH", "XOAUTH2 " + auth_bs64)
            if code != 235:
                raise Exception(f"XOAUTH2 failed with code {code}")
        else:
            # Fallback to plain password (requires SMTP_PASSWORD secret)
            password = os.getenv("SMTP_PASSWORD")
            if not password:
                raise Exception("SMTP_PASSWORD not set")
            server.login(gmail_user, password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"SMTP error: {e}")

@app.post("/contact")
async def contact_form(
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    consent: bool = Form(...)
):
    if not name or not email or not message:
        raise HTTPException(400, "All fields are required")
    if not consent:
        raise HTTPException(400, "You must consent to data processing")
    db = SessionLocal()
    contact = ContactMessage(
        name=name,
        email=email,
        subject=subject,
        message=message
    )
    db.add(contact)
    db.commit()
    db.close()
    send_email_notification(name, email, subject, message)
    return {"status": "success", "message": "Your message has been received. We'll get back to you within 24 hours."}

# ========================
# CORE ENDPOINTS
# ========================
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/agents")
async def list_agents():
    return {"agents": list(AGENT_REGISTRY.keys())}

@app.post("/run-agent")
async def run_agent(
    agent_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(400, f"Unknown agent: {agent_name}")
    content = ""
    if file:
        file_bytes = await file.read()
        content = await extract_text_from_file(file_bytes, file.filename)
    elif text:
        content = text
    else:
        raise HTTPException(400, "No input provided")
    if len(content.strip()) < 50:
        raise HTTPException(400, "Input too short")
    cache_key = get_cache_key(content, agent_name)
    cached = get_cached_response(cache_key)
    if cached:
        return cached
    handler = AGENT_REGISTRY[agent_name]
    result = await handler(content)
    set_cached_response(cache_key, result)
    await save_history_if_user(current_user, agent_name, content, result)
    return result

# ---- Legacy endpoints (keep as before) ----
# ... (all legacy endpoints like /analyze, /dpdp-check, etc.)
# They are identical to your previous version – no changes needed.

# The app is ready.