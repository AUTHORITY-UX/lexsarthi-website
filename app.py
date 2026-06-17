# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os
import json
import io
import hashlib
import re
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

# ---------- App ----------
app = FastAPI(title="LexSarthi API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://advocacyalawfrim.in",
        "https://www.advocacyalawfrim.in",
        "https://lexsarthi-website.pages.dev",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

Base.metadata.create_all(bind=engine)

# ---------- Auth ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
# DEFINE ALL AGENTS
# ========================

# ---- 1. Contract Risk (Enhanced) ----
@register_agent("contract_risk")
async def analyze_contract_risk(text: str) -> dict:
    system = """
You are a senior corporate lawyer with 40 years of experience in Indian contract law, arbitration, and commercial transactions. Your task is to produce a **complete, board‑ready contract analysis** that includes:

1. **Clause‑by‑Clause Analysis** – For each clause, provide:
   - `clause_number` (e.g., "Section 4.2")
   - `title` (e.g., "Indemnity")
   - `risk_level` (Low/Medium/High)
   - `legal_basis` – specific Indian law (e.g., "Section 124 of Indian Contract Act")
   - `reason` – a 2‑3 sentence explanation of the risk
   - `redline` – **EXACT full text of the clause as it should be rewritten**. This must be a complete, ready‑to‑use clause. Never say "No change". If the clause is already perfect, provide a minor improvement (e.g., adding a notice period, clarifying liability cap).

2. **Missing Essential Clauses** – Identify any of the following that are missing:
   - Limitation of Liability
   - Indemnity
   - Termination for Convenience
   - DPDP Act Compliance
   - Non‑Compete / Non‑Solicit
   - Arbitration (Indian seat, Indian law)
   - Governing Law (India)
   - Force Majeure
   - Entire Agreement
   - Amendment
   - Severability
   - Waiver
   - Assignment

   For each missing clause, provide:
   - `title` – name of the missing clause
   - `legal_basis` – relevant law
   - `reason` – why it's essential
   - `proposed_clause_text` – **a complete, ready‑to‑use draft clause** that would make the contract compliant and protective.

3. **Overall Risk Assessment** – assign `overall_risk` (Low/Medium/High) and an `executive_summary` (2‑3 paragraphs suitable for a board report).

**Output JSON** exactly as:
{
  "clause_analysis": [...],
  "missing_clauses": [...],
  "overall_risk": "...",
  "executive_summary": "..."
}

IMPORTANT: Every `redline` and `proposed_clause_text` must be a **full, standalone clause** – not a suggestion or a note. They must be ready to copy and paste directly into the contract. Never output "No change" or "N/A". If the clause is adequate, improve it with a minor but specific enhancement.
"""
    user = f"Contract:\n{text[:15000]}"
    raw = await call_llm(system, user, json_mode=True)
    data = extract_json_from_text(raw)
    # Fallback for missing clauses
    missing = data.get("missing_clauses", [])
    if isinstance(missing, list):
        for idx, clause in enumerate(missing):
            if not isinstance(clause, dict):
                if isinstance(clause, str):
                    missing[idx] = {
                        "title": clause,
                        "legal_basis": "Indian Contract Act",
                        "reason": "This essential clause is missing.",
                        "proposed_clause_text": f"The parties shall include a comprehensive {clause} clause that protects the interests of both parties."
                    }
                continue
            if not clause.get("proposed_clause_text") or len(clause["proposed_clause_text"].strip()) < 10:
                clause["proposed_clause_text"] = (
                    f"The parties shall include a comprehensive {clause.get('title', 'clause')} clause "
                    f"that addresses {clause.get('legal_basis', 'applicable law')} and protects the interests "
                    f"of both parties."
                )
    else:
        data["missing_clauses"] = []
    return data

# ---- 2. DPDP Check ----
@register_agent("dpdp_check")
async def check_dpdp(text: str) -> dict:
    system = """You are a DPDP Act specialist. Analyse the provided privacy policy/data processing document for compliance with India's Digital Personal Data Protection Act, 2023.
Output JSON: {"compliance_score": "High/Medium/Low", "violations": [{"provision": "...", "risk": "...", "redline": "..."}], "executive_summary": "..."}"""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 3. Legal Notice ----
@register_agent("legal_notice")
async def draft_legal_notice(text: str) -> dict:
    system = """You are a litigation lawyer. Draft a formal legal notice based on the facts. Include notice_text, key_legal_basis, suggested_action, lawyer_comments. Output JSON."""
    user = f"Facts:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 4. Due Diligence ----
@register_agent("due_diligence")
async def perform_due_diligence(text: str) -> dict:
    system = """You are a due diligence expert. Analyse the provided documents and produce a report. Output JSON: {"red_flags": [...], "overall_risk": "...", "summary": "..."}"""
    user = f"Documents summary:\n{text[:15000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 5. NDA Triage ----
@register_agent("nda_triage")
async def triage_nda(text: str) -> dict:
    system = """You are an NDA expert. Classify the NDA and highlight risks. Output JSON: {"risk_level": "...", "problematic_clauses": [...], "executive_summary": "..."}"""
    user = f"NDA:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 6. Weekly Digest ----
@register_agent("weekly_digest")
async def generate_digest(text: str) -> dict:
    system = f"""You are a legal assistant. Summarise key legal developments related to '{text}'. Output JSON: {{"digest": [...], "sources": [...], "executive_summary": "..."}}"""
    raw = await call_llm(system, user="Generate digest", json_mode=True)
    return extract_json_from_text(raw)

# ---- 7. Consent Form ----
@register_agent("consent_form")
async def generate_consent(text: str) -> dict:
    system = f"""You are a privacy lawyer. Generate a comprehensive consent form. Purpose/data: {text}. Output JSON: {{"form_title": "...", "consent_text": "...", "required_disclosures": [...], "data_broker_registration_info": {{...}}}}"""
    raw = await call_llm(system, user="Generate consent form", json_mode=True)
    return extract_json_from_text(raw)

# ---- 8. Domain Review ----
@register_agent("domain_review")
async def analyze_domain_agreement(text: str) -> dict:
    system = """You are a domain agreement expert. Extract every clause and provide clause‑wise analysis. Output JSON matching DomainReviewResponse schema."""
    user = f"Domain Agreement:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    data = extract_json_from_text(raw)
    for c in data.get("clauses", []):
        c["clause_number"] = str(c.get("clause_number", ""))
        if not c.get("suggested_change") or c["suggested_change"].strip().lower() in ["no change", "none", "n/a"]:
            c["suggested_change"] = f"Review this clause to address {c.get('risk', 'Medium')} risk."
    return data

# ---- 9. Oral Arguments ----
@register_agent("oral_arguments")
async def prepare_oral_arguments(text: str) -> dict:
    system = """You are a senior advocate. Prepare oral argument strategy. Output JSON with case_summary, issues (with argument, counterarguments, etc.), likely_questions, opening_statement, closing_statement, red_flags, must_cite."""
    user = f"Case details:\n{text[:15000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 10. M&A Due Diligence ----
@register_agent("ma_due_diligence")
async def ma_due_diligence(text: str) -> dict:
    system = """You are a senior M&A lawyer. Analyse the provided documents and produce a due diligence report. Include deal_summary, key_risks, material_contracts, compliance_gaps, conditions_precedent, overall_risk, executive_summary. Output JSON."""
    user = f"Documents:\n{text[:15000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 11. Employment Law ----
@register_agent("employment_law")
async def employment_law(text: str) -> dict:
    system = """You are an employment law expert. Analyse the provided employment contract or policy. Include compliance_score, key_issues, missing_clauses, recommendations, executive_summary. Output JSON."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 12. IP Filing ----
@register_agent("ip_filing")
async def ip_filing(text: str) -> dict:
    system = """You are an IP lawyer. Provide patentability / trademark registrability assessment, strategy, draft claims. Output JSON: {"ip_type": "...", "registrability": "...", "strategy": [...], "prior_art_keywords": [...], "draft_claims": "...", "estimated_timeline": "...", "estimated_cost": "...", "executive_summary": "..."}"""
    user = f"Details:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 13. Tax Compliance ----
@register_agent("tax_compliance")
async def tax_compliance(text: str) -> dict:
    system = """You are a tax lawyer. Review the document for compliance with Indian tax laws. Include compliance_rating, tax_risks, gst_obligations, recommendations, executive_summary. Output JSON."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 14. Real Estate & RERA ----
@register_agent("real_estate_review")
async def real_estate_review(text: str) -> dict:
    system = """You are a real estate lawyer. Analyse the property agreement. Include property_summary, title_risk, rera_compliance, key_issues, recommendations, executive_summary. Output JSON."""
    user = f"Agreement:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 15. Competition Law ----
@register_agent("competition_law")
async def competition_law(text: str) -> dict:
    system = """You are a competition law expert. Analyse the document for anti-competitive practices. Include risk_level, violations, merger_control_required, recommendations, executive_summary. Output JSON."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ---- 16. Data Privacy (Global) ----
@register_agent("data_privacy")
async def data_privacy(text: str) -> dict:
    system = """You are a data privacy lawyer. Analyse the document for DPDP, GDPR, and global compliance. Include global_compliance_score, dpdp_gaps, gdpr_gaps, rights_adequacy, recommendations, executive_summary. Output JSON."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return extract_json_from_text(raw)

# ========================
# AUTH ENDPOINTS
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

# ---- Legacy endpoints (for backward compatibility) ----
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...), lawyer_review: bool = Form(False), current_user: Optional[User] = Depends(get_current_user_optional)):
    result = await run_agent(agent_name="contract_risk", file=file, current_user=current_user)
    return add_lawyer_review(result, lawyer_review)

@app.post("/dpdp-check")
async def dpdp_check(request: dict, current_user: Optional[User] = Depends(get_current_user_optional)):
    text = request.get("text", "")
    result = await run_agent(agent_name="dpdp_check", text=text, current_user=current_user)
    return add_lawyer_review(result, request.get("lawyer_review", False))

@app.post("/legal-notice")
async def legal_notice(request: dict, current_user: Optional[User] = Depends(get_current_user_optional)):
    sender = request.get("sender", "")
    recipient = request.get("recipient", "")
    details = request.get("details", "")
    if not sender or not recipient or not details:
        raise HTTPException(400, "Missing fields")
    prompt = f"Sender: {sender}\nRecipient: {recipient}\nDispute: {details}"
    result = await run_agent(agent_name="legal_notice", text=prompt, current_user=current_user)
    return add_lawyer_review(result, request.get("lawyer_review", False))

@app.post("/due-diligence")
async def due_diligence(files: List[UploadFile] = File(...), lawyer_review: bool = Form(False), current_user: Optional[User] = Depends(get_current_user_optional)):
    combined = ""
    for f in files:
        content = await f.read()
        txt = await extract_text_from_file(content, f.filename)
        combined += f"\n===== {f.filename} =====\n{txt[:2000]}\n"
    result = await run_agent(agent_name="due_diligence", text=combined[:15000], current_user=current_user)
    return add_lawyer_review(result, lawyer_review)

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...), lawyer_review: bool = Form(False), current_user: Optional[User] = Depends(get_current_user_optional)):
    result = await run_agent(agent_name="nda_triage", file=file, current_user=current_user)
    return add_lawyer_review(result, lawyer_review)

@app.get("/weekly-digest")
async def weekly_digest(q: Optional[str] = None, lawyer_review: bool = False, current_user: Optional[User] = Depends(get_current_user_optional)):
    topic = q or "recent legal developments in India"
    result = await run_agent(agent_name="weekly_digest", text=topic, current_user=current_user)
    return add_lawyer_review(result, lawyer_review)

@app.post("/consent-form")
async def consent_form(request: dict, current_user: Optional[User] = Depends(get_current_user_optional)):
    purpose = request.get("purpose", "")
    data = request.get("data_collected", "")
    if not purpose or not data:
        raise HTTPException(400, "Missing purpose or data")
    result = await run_agent(agent_name="consent_form", text=f"Purpose: {purpose}\nData: {data}", current_user=current_user)
    return add_lawyer_review(result, request.get("lawyer_review", False))

@app.post("/domain-review", response_model=DomainReviewResponse)
async def domain_review(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    payment_id: str = Form(...),
    plan: Literal["500", "1000"] = Form(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # Verify payment
    try:
        payment = rzp_client.payment.fetch(payment_id)
        if payment['status'] != 'captured':
            raise HTTPException(400, "Payment not captured")
        expected_amount = int(plan) * 100
        if payment['amount'] != expected_amount:
            raise HTTPException(400, "Payment amount mismatch")
    except Exception as e:
        raise HTTPException(400, f"Payment verification failed: {str(e)}")
    
    result = await run_agent(agent_name="domain_review", file=file, text=text, current_user=current_user)
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

@app.post("/oral-arguments")
async def oral_arguments(text: str = Form(...), lawyer_review: bool = Form(False), current_user: Optional[User] = Depends(get_current_user_optional)):
    result = await run_agent(agent_name="oral_arguments", text=text, current_user=current_user)
    return add_lawyer_review(result, lawyer_review)

# ========================
# SCHEMAS (for Domain Review)
# ========================
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