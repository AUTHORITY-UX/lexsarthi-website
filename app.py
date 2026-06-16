# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os
import json
import io
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Literal
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import PyPDF2
import pdfplumber
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ---------- Authentication & DB (optional) ----------
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt

# ---------- App ----------
app = FastAPI(title="LexSarthi API", version="2.0")

# CORS – allow your frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://advocacyalawfrim.in",
        "https://www.advocacyalawfrim.in",
        "https://dbeba57b.lexsarthi-website.pages.dev",
        "https://lexsarthi-website.pages.dev",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Database Setup (optional) ----------
SQLALCHEMY_DATABASE_URL = "sqlite:///./lexsarthi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------- Models ----------
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

Base.metadata.create_all(bind=engine)

# ---------- Password & JWT ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)  # auto_error=False makes it optional

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ---------- Optional dependency: get current user (returns None if not authenticated) ----------
async def get_current_user_optional(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        db.close()
        return user
    except:
        return None

# ---------- OpenRouter Client ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
MODEL = "meta-llama/llama-3.1-8b-instruct"
MAX_TOKENS_PER_CHUNK = 120000
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# ---------- Pydantic Schemas ----------
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

def split_text_with_overlap(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    tokens = TOKEN_ENCODER.encode(text)
    if len(tokens) <= max_tokens:
        return [text]
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = TOKEN_ENCODER.decode(chunk_tokens)
        chunks.append(chunk_text)
        if end >= len(tokens):
            break
        start = end - overlap_tokens
    return chunks

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

# ---------- Lawyer Review Profile ----------
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

# ---------- Save History Helper (only if user logged in) ----------
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
# AUTH ENDPOINTS (still functional)
# ========================

@app.post("/signup", response_model=Token)
async def signup(user: UserCreate):
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
# AGENT HANDLERS (unchanged)
# ========================
async def analyze_contract_risk(text: str) -> dict:
    system = """
You are a senior corporate lawyer with 40 years of experience in Indian contract law, arbitration, and commercial transactions.
Analyse the provided contract and produce a polished board‑ready report.

For each clause, provide:
- clause_number
- title
- risk_level (Low/Medium/High)
- legal_basis (specific Indian law, e.g., Contract Act, DPDP Act, IBC)
- reason (2‑3 sentences)
- redline (EXACT suggested replacement text – NEVER "No change"; suggest a minor improvement if perfect)

Also identify missing essential clauses: limitation of liability, indemnity, termination for convenience, DPDP Act compliance, non‑compete, non‑solicit, arbitration (Indian seat), governing law India, force majeure, entire agreement, amendment, severability, waiver, assignment. For each missing clause, propose a draft clause.

Output JSON:
{
  "clause_analysis": [...],
  "missing_clauses": [...],
  "overall_risk": "Low/Medium/High",
  "executive_summary": "..."
}
"""
    user = f"Contract:\n{text[:15000]}"
    raw = await call_llm(system, user)
    return extract_json_from_text(raw)

async def check_dpdp(text: str) -> dict:
    system = """
You are a DPDP Act specialist. Analyse the provided privacy policy/data processing document for compliance with India's Digital Personal Data Protection Act, 2023.
Output JSON:
{
  "compliance_score": "High/Medium/Low",
  "violations": [{"provision": "...", "risk": "...", "redline": "..."}],
  "executive_summary": "..."
}
"""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return extract_json_from_text(raw)

async def draft_legal_notice(text: str) -> dict:
    system = """
You are a litigation lawyer. Draft a formal legal notice based on the facts. Include:
- notice_text (full notice with to, from, subject, body, deadline)
- key_legal_basis (relevant Indian laws)
- suggested_action (what sender should do next)
- lawyer_comments (as if a senior advocate reviewed it)
Output JSON:
{
  "notice_text": "...",
  "key_legal_basis": "...",
  "suggested_action": "...",
  "lawyer_comments": "..."
}
"""
    user = f"Facts:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

async def perform_due_diligence(text: str) -> dict:
    system = """
You are a due diligence expert. Analyse the provided documents and produce a report.
Output JSON:
{
  "red_flags": [{"document": "...", "clause": "...", "risk": "...", "action": "..."}],
  "overall_risk": "Low/Medium/High",
  "summary": "..."
}
"""
    user = f"Documents summary:\n{text[:15000]}"
    raw = await call_llm(system, user)
    return extract_json_from_text(raw)

async def triage_nda(text: str) -> dict:
    system = """
You are an NDA expert. Classify the NDA and highlight risks.
Output JSON:
{
  "risk_level": "Low/Medium/High",
  "problematic_clauses": [{"clause": "...", "reason": "...", "redline": "..."}],
  "executive_summary": "..."
}
"""
    user = f"NDA:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return extract_json_from_text(raw)

async def generate_digest(topic: str) -> dict:
    system = f"""
You are a legal assistant. Summarise key legal developments in India and globally related to '{topic}'.
Output JSON:
{{
  "digest": ["point1", "point2", "point3"],
  "sources": ["law", "judgment", "article"],
  "executive_summary": "..."
}}
"""
    raw = await call_llm(system, user="Generate digest", json_mode=True)
    return extract_json_from_text(raw)

async def generate_consent(purpose: str, data_collected: str) -> dict:
    system = f"""
You are a privacy lawyer. Generate a comprehensive consent form under the DPDP Act and GDPR principles.
Purpose: {purpose}
Data collected: {data_collected}
Output JSON:
{{
  "form_title": "Consent Form",
  "consent_text": "Full consent text...",
  "required_disclosures": ["list", "of", "disclosures"],
  "data_broker_registration_info": {{"registration_required": true/false, "fee_info": "...", "audit_requirement": "..."}}
}}
"""
    raw = await call_llm(system, user="Generate consent form", json_mode=True)
    return extract_json_from_text(raw)

async def analyze_domain_agreement(text: str) -> dict:
    system = """
You are a domain agreement expert. Extract every clause and provide clause‑wise analysis.
For each clause: clause_number, clause_text, risk (Low/Medium/High/Critical), summary, suggested_change (MANDATORY, never "no change"), actionable (bool), reason.
Also provide agreement_type, overall_risk, executive_summary.
Output JSON matching the DomainReviewResponse schema.
"""
    user = f"Domain Agreement:\n{text[:12000]}"
    raw = await call_llm(system, user)
    data = extract_json_from_text(raw)
    
    # --- FIX: Ensure clause_number is always a string ---
    for c in data.get("clauses", []):
        # Convert clause_number to string if it's an integer
        if "clause_number" in c:
            c["clause_number"] = str(c["clause_number"])
        # Also ensure suggested_change is never empty
        if not c.get("suggested_change") or c["suggested_change"].strip().lower() in ["no change", "none", "n/a"]:
            c["suggested_change"] = f"Review this clause to address {c.get('risk', 'Medium')} risk."
        # Ensure actionable is a boolean (in case LLM returns string)
        if "actionable" in c and isinstance(c["actionable"], str):
            c["actionable"] = c["actionable"].lower() in ["true", "1", "yes"]
    
    return data

# ========================
# GENERIC PROCESSOR (with optional auth)
# ========================
async def process_analysis(agent_name: str, file: UploadFile = None, text: str = None, user: Optional[User] = None):
    content = ""
    if file:
        file_bytes = await file.read()
        content = await extract_text_from_file(file_bytes, file.filename)
    elif text:
        content = text
    else:
        raise HTTPException(400, "No input")
    if len(content.strip()) < 50:
        raise HTTPException(400, "Input too short")

    handlers = {
        "contract_risk": analyze_contract_risk,
        "dpdp_check": check_dpdp,
        "legal_notice": draft_legal_notice,
        "due_diligence": perform_due_diligence,
        "nda_triage": triage_nda,
        "weekly_digest": lambda t: generate_digest(t),
        "consent_form": lambda t: generate_consent(t, ""),
        "domain_review": analyze_domain_agreement,
    }
    if agent_name not in handlers:
        raise HTTPException(400, f"Unknown agent: {agent_name}")
    result = await handlers[agent_name](content)
    # Save history only if user is authenticated
    await save_history_if_user(user, agent_name, content, result)
    return result

# ========================
# API ENDPOINTS (all public, auth optional)
# ========================

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/run-agent")
async def run_agent(
    agent_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    return await process_analysis(agent_name, file, text, current_user)

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    lawyer_review: bool = Form(False),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    result = await process_analysis("contract_risk", file, None, current_user)
    return add_lawyer_review(result, lawyer_review)

@app.post("/dpdp-check")
async def dpdp_check(
    request: dict,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    text = request.get("text", "")
    lawyer = request.get("lawyer_review", False)
    result = await process_analysis("dpdp_check", None, text, current_user)
    return add_lawyer_review(result, lawyer)

@app.post("/legal-notice")
async def legal_notice(
    request: dict,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    sender = request.get("sender", "")
    recipient = request.get("recipient", "")
    details = request.get("details", "")
    lawyer = request.get("lawyer_review", False)
    if not sender or not recipient or not details:
        raise HTTPException(400, "Missing fields")
    prompt = f"Sender: {sender}\nRecipient: {recipient}\nDispute: {details}"
    result = await process_analysis("legal_notice", None, prompt, current_user)
    return add_lawyer_review(result, lawyer)

@app.post("/due-diligence")
async def due_diligence(
    files: List[UploadFile] = File(...),
    lawyer_review: bool = Form(False),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    combined = ""
    for f in files:
        content = await f.read()
        txt = await extract_text_from_file(content, f.filename)
        combined += f"\n===== {f.filename} =====\n{txt[:2000]}\n"
    result = await process_analysis("due_diligence", None, combined[:15000], current_user)
    return add_lawyer_review(result, lawyer_review)

@app.post("/nda-triage")
async def nda_triage(
    file: UploadFile = File(...),
    lawyer_review: bool = Form(False),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    result = await process_analysis("nda_triage", file, None, current_user)
    return add_lawyer_review(result, lawyer_review)

@app.get("/weekly-digest")
async def weekly_digest(
    q: Optional[str] = None,
    lawyer_review: bool = False,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    topic = q or "recent legal developments in India"
    result = await process_analysis("weekly_digest", None, topic, current_user)
    return add_lawyer_review(result, lawyer_review)

@app.post("/consent-form")
async def consent_form(
    request: dict,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    purpose = request.get("purpose", "")
    data = request.get("data_collected", "")
    lawyer = request.get("lawyer_review", False)
    if not purpose or not data:
        raise HTTPException(400, "Missing purpose or data")
    result = await process_analysis("consent_form", None, f"Purpose: {purpose}\nData: {data}", current_user)
    return add_lawyer_review(result, lawyer)

@app.post("/domain-review", response_model=DomainReviewResponse)
async def domain_review(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    payment_id: str = Form(...),
    plan: Literal["500", "1000"] = Form(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # You should verify payment with Razorpay here using payment_id
    # For now, we assume payment is valid.
    result = await process_analysis("domain_review", file, text, current_user)
    is_lawyer = (plan == "1000")
    review_id = f"REV-{payment_id[-8:]}" if is_lawyer else None
    return DomainReviewResponse(
        agreement_type=result.get("agreement_type", "Other"),
        overall_risk=result.get("overall_risk", "Medium"),
        executive_summary=result.get("executive_summary", ""),
        clauses=[ClauseReview(**c) for c in result.get("clauses", [])],
        lawyer_review_required=is_lawyer,
        review_id=review_id
    )