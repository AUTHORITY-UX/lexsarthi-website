# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.
# ===================================================================
# LexSarthi v2.0 – Complete Legal Automation System
# - JSON output with structured legal analysis
# - Chunking with overlap for complete document analysis
# - Verifier Agent for hallucination detection
# - Lawyer review/redrafting integration (PRESERVED)
# - Risk parameters with quantitative scoring (0-100)
# - 16 specialised agents with codified act references
# ===================================================================

import os
import json
import sqlite3
import jwt
import hashlib
import datetime
import re
from typing import Optional, Tuple, List, Dict, Any
from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
import httpx
from pydantic import BaseModel, EmailStr
import razorpay

# ---------- CONFIGURATION ----------
SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DATABASE_URL = "/data/lexsarthi.db"

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

ADMIN_KEY = os.environ["ADMIN_KEY"]

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET else None

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_CHUNK_TOKENS = 90000
OVERLAP_TOKENS = 3000

app = FastAPI(title="LexSarthi API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
templates = Jinja2Templates(directory="templates")

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            consent_given BOOLEAN DEFAULT 0,
            consent_timestamp TIMESTAMP,
            consent_version TEXT DEFAULT 'v1.0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            plan TEXT DEFAULT 'starter',
            subscription_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent TEXT NOT NULL,
            input_text TEXT,
            result_json TEXT,
            verifier_output TEXT,
            lawyer_reviewed BOOLEAN DEFAULT 0,
            lawyer_comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT,
            consent BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            razorpay_order_id TEXT UNIQUE,
            razorpay_payment_id TEXT,
            razorpay_signature TEXT,
            amount INTEGER,
            currency TEXT DEFAULT 'INR',
            plan TEXT,
            status TEXT DEFAULT 'created',
            receipt TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- HELPERS ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def estimate_tokens(text: str) -> int:
    return len(text) // 4

# ---------- CHUNKING ----------
def split_into_chunks(text: str, max_tokens: int = MAX_CHUNK_TOKENS, overlap_tokens: int = OVERLAP_TOKENS) -> List[str]:
    if estimate_tokens(text) <= max_tokens:
        return [text]
    
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if current_tokens + para_tokens <= max_tokens:
            current_chunk.append(para)
            current_tokens += para_tokens
        else:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                overlap_paras = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_paras.copy()
                current_tokens = sum(estimate_tokens(p) for p in current_chunk)
            current_chunk.append(para)
            current_tokens += para_tokens
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

# ---------- MERGE CHUNK RESULTS ----------
def merge_chunk_results(results: List[dict]) -> dict:
    """Merge multiple chunk analyses into a single comprehensive JSON."""
    if not results:
        return {"error": "No analysis results to merge"}
    
    if len(results) == 1:
        return results[0]
    
    merged = {
        "executive_summary": "",
        "overall_risk": "Low",
        "risk_score": 0,
        "clause_analysis": [],
        "missing_clauses": [],
        "risk_breakdown": {"High": 0, "Medium": 0, "Low": 0},
        "total_clauses_analysed": 0,
        "chunks_processed": len(results),
        "recommendations": [],
        "redlines": []
    }
    
    seen_clauses = set()
    seen_missing = set()
    risk_counts = {"Low": 0, "Medium": 0, "High": 0}
    all_recommendations = []
    all_redlines = []
    
    for result in results:
        for clause in result.get("clause_analysis", []):
            clause_key = clause.get("clause_number", "") + clause.get("clause_text", "")[:50]
            if clause_key not in seen_clauses:
                seen_clauses.add(clause_key)
                merged["clause_analysis"].append(clause)
                risk = clause.get("risk_level", "Medium")
                if risk in risk_counts:
                    risk_counts[risk] += 1
                if "redline" in clause and clause["redline"]:
                    all_redlines.append(clause["redline"])
        
        for missing in result.get("missing_clauses", []):
            title_key = missing.get("title", "")
            if title_key and title_key not in seen_missing:
                seen_missing.add(title_key)
                merged["missing_clauses"].append(missing)
        
        if "recommendations" in result:
            all_recommendations.extend(result.get("recommendations", []))
    
    merged["risk_breakdown"] = risk_counts
    merged["total_clauses_analysed"] = len(merged["clause_analysis"])
    
    # Calculate risk score
    total_risk = sum(risk_counts["High"] * 90 + risk_counts["Medium"] * 50 + risk_counts["Low"] * 10)
    max_risk = max(1, sum(risk_counts.values()) * 90)
    risk_score = min(100, int((total_risk / max_risk) * 100))
    merged["risk_score"] = risk_score
    
    if risk_score >= 70:
        merged["overall_risk"] = "High"
    elif risk_score >= 40:
        merged["overall_risk"] = "Medium"
    else:
        merged["overall_risk"] = "Low"
    
    merged["executive_summary"] = (
        f"Comprehensive analysis complete.\n"
        f"Clauses analysed: {len(merged['clause_analysis'])}\n"
        f"Missing clauses: {len(merged['missing_clauses'])}\n"
        f"Risk Score: {risk_score}/100 ({merged['overall_risk']} Risk)\n"
        f"High: {risk_counts['High']}, Medium: {risk_counts['Medium']}, Low: {risk_counts['Low']}\n"
        f"Chunks processed: {len(results)}"
    )
    
    merged["recommendations"] = list(set(all_recommendations))[:10] if all_recommendations else []
    merged["redlines"] = all_redlines[:20] if all_redlines else []
    
    return merged

# ---------- VERIFIER AGENT ----------
async def verify_analysis(original_text: str, analysis_result: dict) -> dict:
    verification_prompt = f"""
You are a senior legal verifier. Cross-check this analysis against the original document.

ORIGINAL EXCERPT:
{original_text[:15000]}

ANALYSIS:
{json.dumps(analysis_result, indent=2)[:10000]}

Check for hallucinations, incorrect citations, missing issues, over/understated risks.

Output JSON:
{{
  "verified": true/false,
  "confidence_score": 0-100,
  "issues_found": ["issue"],
  "hallucinations": ["hallucination"],
  "incorrect_citations": ["citation"],
  "missing_critical_issues": ["issue"],
  "recommendation": "Accept/Review/Reject",
  "verifier_comments": "Detailed comments"
}}
"""
    try:
        messages = [
            {"role": "system", "content": "You are a senior legal verifier. Output JSON only."},
            {"role": "user", "content": verification_prompt}
        ]
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 3000
                },
                timeout=120.0
            )
            if response.status_code != 200:
                return {"verified": False, "error": response.text}
            data = response.json()
            return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        return {"verified": False, "error": str(e)}

# ---------- MODELS ----------
class UserRegister(BaseModel):
    username: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ContactForm(BaseModel):
    name: str
    email: str
    subject: str
    message: str
    consent: bool = True

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class GrievanceRequest(BaseModel):
    subject: str
    message: str

class PaymentOrderRequest(BaseModel):
    plan: str
    amount: int

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

# ---------- AGENTS ----------
AGENTS = [
    {"id": "contract_review", "name": "Contract Review", "icon": "📄", "description": "Analyse contracts for risks, missing clauses, and redlines."},
    {"id": "due_diligence", "name": "Due Diligence", "icon": "🔍", "description": "M&A due diligence, identify legal red flags."},
    {"id": "legal_research", "name": "Legal Research", "icon": "📚", "description": "Research case law, statutes, and legal principles."},
    {"id": "domain_review", "name": "Domain Review", "icon": "🌐", "description": "Review domain name disputes and trademark issues."},
    {"id": "nda", "name": "NDA Analysis", "icon": "🤝", "description": "Analyse non-disclosure agreements."},
    {"id": "employment", "name": "Employment Contract", "icon": "👔", "description": "Review employment agreements and HR policies."},
    {"id": "ip", "name": "Intellectual Property", "icon": "💡", "description": "IP registration, licensing, and infringement analysis."},
    {"id": "tax", "name": "Tax Structuring", "icon": "💰", "description": "Tax planning, GST, and compliance."},
    {"id": "compliance", "name": "Regulatory Compliance", "icon": "✅", "description": "Check compliance with DPDP, GDPR, IBC, etc."},
    {"id": "litigation", "name": "Litigation Risk", "icon": "⚖️", "description": "Assess litigation risks and strategy."},
    {"id": "corporate", "name": "Corporate Governance", "icon": "🏢", "description": "Board resolutions, shareholder agreements."},
    {"id": "real_estate", "name": "Real Estate", "icon": "🏠", "description": "Property agreements, title verification."},
    {"id": "finance", "name": "Finance & Banking", "icon": "🏦", "description": "Loan agreements, security documents."},
    {"id": "data_protection", "name": "Data Protection", "icon": "🔒", "description": "DPDP Act, GDPR, privacy policies."},
    {"id": "insolvency", "name": "Insolvency & Bankruptcy", "icon": "📉", "description": "IBC, insolvency risk assessment."},
    {"id": "arbitration", "name": "Arbitration & Dispute", "icon": "⚡", "description": "Arbitration clauses and dispute resolution."}
]

# ---------- AGENT PROMPTS ----------
AGENT_PROMPTS = {
    "contract_review": """
You are a senior corporate lawyer. Analyse the contract and reference specific sections of the Indian Contract Act, 1872.

Output JSON:
{
  "executive_summary": "Overall assessment (max 200 chars)",
  "overall_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "clause_analysis": [
    {"clause_number": "...", "clause_text": "...", "section_reference": "Section X, Contract Act", "legal_basis": "...", "risk_level": "High/Medium/Low", "reason": "...", "redline": "suggested text"}
  ],
  "missing_clauses": [
    {"title": "...", "legal_basis": "Section X, Contract Act", "reason": "...", "proposed_clause_text": "..."}
  ],
  "recommendations": ["rec 1", "rec 2"]
}
""",
    "due_diligence": """
You are a due diligence expert. Reference the Companies Act, 2013 and SEBI regulations.

Output JSON:
{
  "executive_summary": "...",
  "overall_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "red_flags": [
    {"document": "...", "clause": "...", "legal_basis": "Section X, Companies Act", "risk": "...", "action": "..."}
  ],
  "recommendations": ["rec"]
}
""",
    "legal_research": """
You are a legal researcher. Cite specific acts, sections, and case laws.

Output JSON:
{
  "executive_summary": "...",
  "relevant_cases": [{"case_name": "...", "citation": "...", "section_reference": "...", "relevance": "..."}],
  "statutes_applicable": [{"statute": "...", "section": "...", "relevance": "..."}],
  "legal_principles": "...",
  "recommendations": ["rec"]
}
""",
    "domain_review": """
You are a domain dispute expert. Reference the IT Act, 2000.

Output JSON:
{
  "executive_summary": "...",
  "overall_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "clauses": [
    {"clause_number": "...", "clause_text": "...", "risk": "...", "legal_basis": "Section X, IT Act", "reason": "...", "suggested_change": "..."}
  ],
  "lawyer_review_required": true
}
""",
    "nda": """
You are an NDA specialist. Reference the Indian Contract Act, 1872.

Output JSON:
{
  "executive_summary": "...",
  "overall_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "problematic_clauses": [
    {"clause": "...", "legal_basis": "Section X, Contract Act", "reason": "...", "redline": "..."}
  ]
}
""",
    "employment": """
You are an employment law expert. Reference the Industrial Disputes Act, 1947, EPF Act, ESI Act.

Output JSON:
{
  "executive_summary": "...",
  "overall_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "clause_analysis": [
    {"clause": "...", "risk": "...", "legal_basis": "Section X, ID Act", "recommendation": "..."}
  ],
  "missing_compliance": ["item"],
  "recommendations": ["rec"]
}
""",
    "ip": """
You are an IP lawyer. Reference Trade Marks Act, 1999, Patents Act, 1970, Copyright Act, 1957.

Output JSON:
{
  "executive_summary": "...",
  "overall_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "ip_assets": [
    {"type": "...", "status": "...", "legal_basis": "Section X, Trade Marks Act", "risk": "...", "recommendation": "..."}
  ],
  "compliance_issues": [
    {"issue": "...", "legal_basis": "Section X, Copyright Act", "recommendation": "..."}
  ]
}
""",
    "tax": """
You are a tax lawyer. Reference Income Tax Act, 1961 and CGST Act, 2017.

Output JSON:
{
  "executive_summary": "...",
  "tax_risks": [
    {"issue": "...", "legal_basis": "Section X, IT Act", "risk": "...", "recommendation": "..."}
  ],
  "compliance_score": "High/Medium/Low",
  "overall_risk": "High/Medium/Low"
}
""",
    "compliance": """
You are a compliance expert. Reference DPDP Act, IBC, RBI, SEBI regulations.

Output JSON:
{
  "executive_summary": "...",
  "violations": [
    {"provision": "Section X, DPDP Act", "legal_basis": "...", "risk": "...", "recommendation": "..."}
  ],
  "compliance_score": "High/Medium/Low"
}
""",
    "litigation": """
You are a litigation lawyer. Reference CPC, 1908, BNSS, 2023, and Evidence Act, 1872.

Output JSON:
{
  "executive_summary": "...",
  "litigation_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "key_legal_issues": [
    {"issue": "...", "legal_basis": "Section X, CPC", "analysis": "..."}
  ],
  "recommended_strategy": "...",
  "estimated_timeline": "..."
}
""",
    "corporate": """
You are a corporate governance expert. Reference the Companies Act, 2013 and SEBI LODR.

Output JSON:
{
  "executive_summary": "...",
  "governance_risks": [
    {"issue": "...", "legal_basis": "Section X, Companies Act", "risk": "...", "recommendation": "..."}
  ],
  "compliance_requirements": ["..."],
  "overall_risk": "High/Medium/Low"
}
""",
    "real_estate": """
You are a real estate lawyer. Reference Transfer of Property Act, RERA, Registration Act.

Output JSON:
{
  "executive_summary": "...",
  "title_issues": [
    {"issue": "...", "legal_basis": "Section X, TP Act", "recommendation": "..."}
  ],
  "regulatory_compliance_issues": [
    {"issue": "...", "legal_basis": "Section X, RERA", "recommendation": "..."}
  ],
  "overall_risk": "High/Medium/Low",
  "recommended_actions": ["..."]
}
""",
    "finance": """
You are a banking lawyer. Reference SARFAESI Act, Banking Regulation Act.

Output JSON:
{
  "executive_summary": "...",
  "key_terms_analysis": {},
  "risk_issues": [
    {"clause": "...", "legal_basis": "Section X, SARFAESI", "risk": "...", "recommendation": "..."}
  ],
  "overall_risk": "High/Medium/Low"
}
""",
    "data_protection": """
You are a data protection lawyer. Reference DPDP Act, 2023 and GDPR.

Output JSON:
{
  "executive_summary": "...",
  "compliance_score": "High/Medium/Low",
  "violations": [
    {"provision": "Section X, DPDP Act", "legal_basis": "...", "risk": "...", "recommendation": "..."}
  ],
  "required_actions": ["..."]
}
""",
    "insolvency": """
You are an insolvency lawyer. Reference IBC, 2016.

Output JSON:
{
  "executive_summary": "...",
  "insolvency_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "key_issues": [
    {"issue": "...", "legal_basis": "Section X, IBC", "recommendation": "..."}
  ],
  "recommended_course_of_action": "...",
  "timeline": "..."
}
""",
    "arbitration": """
You are an arbitration lawyer. Reference Arbitration Act, 1996.

Output JSON:
{
  "executive_summary": "...",
  "arbitration_risk": "High/Medium/Low",
  "risk_score": 0-100,
  "key_clauses_analysis": [
    {"clause": "...", "legal_basis": "Section X, Arbitration Act", "analysis": "..."}
  ],
  "recommendations": ["..."]
}
"""
}

# ---------- DOCUMENT GENERATION PROMPTS ----------
DOCUMENT_PROMPTS = {
    "bail": """
Draft a bail application under BNSS, 2023.

FACTS: {facts}
Court: {court_name}
Case: {case_number}
Accused: {parties}

Output JSON:
{
  "document_title": "Bail Application under BNSS, 2023",
  "format": "Section 480, BNSS, 2023",
  "content": "Full draft...",
  "legal_basis": ["Section 480, BNSS", "Section 482, BNSS"],
  "grounds": [{"ground": "...", "legal_basis": "Section X, BNSS"}],
  "checklist": ["..."]
}
""",
    "writ": """
Draft a writ petition under Article 226, Constitution of India.

FACTS: {facts}
Court: {court_name}
Case: {case_number}
Petitioner: {parties}

Output JSON:
{
  "document_title": "Writ Petition under Article 226",
  "format": "Article 226, Constitution of India",
  "content": "Full draft...",
  "legal_basis": ["Article 226", "Article 14", "Article 21"],
  "grounds": [{"ground": "...", "legal_basis": "Article X"}],
  "relief_sought": ["..."]
}
""",
    "plaint": """
Draft a plaint under CPC, 1908.

FACTS: {facts}
Court: {court_name}
Case: {case_number}
Parties: {parties}

Output JSON:
{
  "document_title": "Plaint under CPC, 1908",
  "format": "Order VI, CPC, 1908",
  "content": "Full draft...",
  "legal_basis": ["Order VI, Rule 1", "Order VI, Rule 2"],
  "relief_sought": ["..."]
}
""",
    "written_statement": """
Draft a written statement under CPC, 1908.

FACTS: {facts}
Court: {court_name}
Case: {case_number}
Parties: {parties}

Output JSON:
{
  "document_title": "Written Statement under CPC, 1908",
  "format": "Order VIII, CPC, 1908",
  "content": "Full draft...",
  "legal_basis": ["Order VIII, Rule 1", "Order VIII, Rule 2"],
  "defences": [{"defence": "...", "legal_basis": "Order VIII, Rule X"}]
}
""",
    "arbitration": """
Draft a statement of claim under Arbitration Act, 1996.

FACTS: {facts}
Parties: {parties}

Output JSON:
{
  "document_title": "Statement of Claim under Arbitration Act",
  "format": "Section 21, Arbitration Act, 1996",
  "content": "Full draft...",
  "legal_basis": ["Section 21", "Section 23"],
  "relief_sought": ["..."]
}
""",
    "appeal": """
Draft a memorandum of appeal under CPC, 1908.

FACTS: {facts}
Court: {court_name}
Case: {case_number}
Parties: {parties}

Output JSON:
{
  "document_title": "Memorandum of Appeal under CPC",
  "format": "Order XLI, CPC, 1908",
  "content": "Full draft...",
  "legal_basis": ["Order XLI, Rule 1", "Order XLI, Rule 2"],
  "grounds_of_appeal": [{"ground": "...", "legal_basis": "Order XLI, Rule X"}]
}
"""
}

# ---------- ENDPOINTS ----------

@app.get("/")
async def root():
    return {"status": "LexSarthi API is live", "version": "2.0"}

@app.get("/agents")
async def list_agents():
    return AGENTS

# ---------- RUN AGENT (COMPLETE ANALYSIS WITH JSON OUTPUT) ----------
@app.post("/run-agent")
async def run_agent(
    agent_name: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    verify: bool = Form(False),
    lawyer_review: bool = Form(False),
    token: str = Depends(oauth2_scheme)
):
    """Complete document analysis with JSON output."""
    
    agent = next((a for a in AGENTS if a["id"] == agent_name), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_name}")

    # Get input text
    input_text = text
    if file:
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Max 50MB.")
        contents = await file.read()
        try:
            input_text = contents.decode("utf-8")
        except:
            input_text = contents.decode("latin-1")
    
    if not input_text:
        raise HTTPException(status_code=400, detail="No input text provided")

    # Chunk the document
    chunks = split_into_chunks(input_text)
    if len(chunks) == 0:
        raise HTTPException(status_code=400, detail="No text extracted.")
    
    print(f"📄 Document split into {len(chunks)} chunks for complete analysis.")

    # Analyse each chunk
    chunk_results = []
    system_prompt = AGENT_PROMPTS.get(agent_name, AGENT_PROMPTS["contract_review"])
    system_prompt += "\n\nOutput in valid JSON format only."

    for idx, chunk in enumerate(chunks):
        chunk_prompt = f"{system_prompt}\n\nDOCUMENT PART {idx+1} OF {len(chunks)}:\n{chunk}"
        
        try:
            messages = [
                {"role": "system", "content": "You are a senior legal expert. Output JSON only."},
                {"role": "user", "content": chunk_prompt}
            ]
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "openai/gpt-4o-mini",
                        "messages": messages,
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                        "max_tokens": 4096
                    }
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
                data = response.json()
                result = json.loads(data["choices"][0]["message"]["content"])
                chunk_results.append(result)
                print(f"✅ Analysed chunk {idx+1}/{len(chunks)}")
        except Exception as e:
            print(f"❌ Failed to analyse chunk {idx+1}: {str(e)}")
            chunk_results.append({
                "executive_summary": f"Error in chunk {idx+1}",
                "overall_risk": "Unknown",
                "clause_analysis": [],
                "missing_clauses": [],
                "error": str(e)
            })
    
    # Merge all chunk results
    final_result = merge_chunk_results(chunk_results)
    final_result["agent_used"] = agent_name
    final_result["chunks_processed"] = len(chunks)
    final_result["total_characters"] = len(input_text)
    
    # Optional: Verifier Agent
    verifier_report = None
    if verify:
        verifier_report = await verify_analysis(input_text[:15000], final_result)
        final_result["verifier_report"] = verifier_report
    
    # Lawyer review flag (PRESERVED - YOUR EXISTING INTEGRATION)
    final_result["lawyer_review_requested"] = lawyer_review
    if lawyer_review:
        final_result["lawyer_review_note"] = (
            "This analysis has been flagged for review by a lawyer. "
            "A senior advocate from Advocacy A Law Firm will review and provide comments within 24 hours."
        )
    
    # Save to history
    try:
        user = get_current_user(token)
        conn = get_db()
        conn.execute(
            "INSERT INTO history (user_id, agent, input_text, result_json, verifier_output, lawyer_reviewed) VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], agent_name, input_text[:500], json.dumps(final_result),
             json.dumps(verifier_report) if verifier_report else None,
             1 if lawyer_review else 0)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ History save failed: {str(e)}")
    
    return final_result

# ---------- GENERATE DOCUMENT ----------
@app.post("/generate-document")
async def generate_document(
    document_type: str = Form(...),
    facts: str = Form(...),
    court_name: Optional[str] = Form(None),
    case_number: Optional[str] = Form(None),
    parties: Optional[str] = Form(None),
    token: str = Depends(oauth2_scheme)
):
    prompt_template = DOCUMENT_PROMPTS.get(document_type)
    if not prompt_template:
        raise HTTPException(400, f"Document type '{document_type}' not supported.")
    
    prompt = prompt_template.format(
        facts=facts,
        court_name=court_name or "[Insert Court Name]",
        case_number=case_number or "[Insert Case Number]",
        parties=parties or "[Insert Parties]"
    )
    
    try:
        messages = [
            {"role": "system", "content": "You are an expert legal drafter. Output JSON only."},
            {"role": "user", "content": prompt}
        ]
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 4096
                }
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            data = response.json()
            result = json.loads(data["choices"][0]["message"]["content"])
            
            user = get_current_user(token)
            conn = get_db()
            conn.execute(
                "INSERT INTO history (user_id, agent, input_text, result_json) VALUES (?, ?, ?, ?)",
                (user["id"], f"document_{document_type}", facts[:500], json.dumps(result))
            )
            conn.commit()
            conn.close()
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")

# ---------- AUTHENTICATION ----------
@app.post("/auth/register")
async def register(user_data: UserRegister):
    conn = get_db()
    existing = conn.execute("SELECT * FROM users WHERE username = ?", (user_data.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(user_data.password)
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name, consent_given, consent_timestamp, consent_version) VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, 'v1.0')",
        (user_data.username, hashed, user_data.full_name)
    )
    conn.commit()
    conn.close()
    token = create_access_token({"sub": user_data.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/login")
async def login(user_data: UserLogin):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (user_data.username,)).fetchone()
    conn.close()
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user_data.username})
    return {"access_token": token, "token_type": "bearer"}

# ---------- DPDP ----------
@app.get("/auth/me")
async def get_my_data(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    hist_count = conn.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (current_user["id"],)).fetchone()[0]
    conn.close()
    return {
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "created_at": current_user["created_at"],
        "consent_given": bool(current_user.get("consent_given", 0)),
        "consent_timestamp": current_user.get("consent_timestamp"),
        "consent_version": current_user.get("consent_version", "v1.0"),
        "history_count": hist_count
    }

@app.post("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    if not verify_password(request.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    new_hash = hash_password(request.new_password)
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, current_user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Password updated successfully"}

@app.delete("/auth/me")
async def delete_account(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM history WHERE user_id = ?", (current_user["id"],))
    conn.execute("DELETE FROM users WHERE id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"message": "Account permanently deleted"}

@app.post("/auth/grievance")
async def file_grievance(
    request: GrievanceRequest,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db()
    conn.execute(
        "INSERT INTO contacts (name, email, subject, message, consent) VALUES (?, ?, ?, ?, ?)",
        (current_user["full_name"], current_user["username"], f"GRIEVANCE: {request.subject}", request.message, 1)
    )
    conn.commit()
    conn.close()
    return {"message": "Grievance submitted. DPO will respond within 30 days."}

@app.post("/auth/consent")
async def update_consent(
    consent_given: bool,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db()
    conn.execute(
        "UPDATE users SET consent_given = ?, consent_timestamp = CURRENT_TIMESTAMP, consent_version = 'v1.0' WHERE id = ?",
        (1 if consent_given else 0, current_user["id"])
    )
    conn.commit()
    conn.close()
    return {"message": f"Consent {'granted' if consent_given else 'withdrawn'}"}

@app.post("/contact")
async def contact(form: ContactForm):
    conn = get_db()
    conn.execute(
        "INSERT INTO contacts (name, email, subject, message, consent) VALUES (?, ?, ?, ?, ?)",
        (form.name, form.email, form.subject, form.message, form.consent)
    )
    conn.commit()
    conn.close()
    return {"message": "Thank you. We'll respond within 24 hours."}

@app.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT agent, input_text, result_json, verifier_output, lawyer_reviewed, created_at FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (current_user["id"],)
    ).fetchall()
    conn.close()
    history = []
    for r in rows:
        history.append({
            "agent": r["agent"],
            "input_text": r["input_text"],
            "result_json": json.loads(r["result_json"]) if r["result_json"] else None,
            "verifier_output": json.loads(r["verifier_output"]) if r["verifier_output"] else None,
            "lawyer_reviewed": bool(r["lawyer_reviewed"]),
            "created_at": r["created_at"]
        })
    return history

# ---------- PAYMENTS ----------
@app.post("/payment/create-order")
async def create_payment_order(
    req: PaymentOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay not configured")

    amount_in_paise = req.amount * 100
    try:
        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_{current_user['id']}_{int(datetime.datetime.utcnow().timestamp())}",
            "notes": {
                "user_id": str(current_user["id"]),
                "email": current_user["username"],
                "plan": req.plan
            }
        }
        order = razorpay_client.order.create(data=order_data)

        conn = get_db()
        conn.execute(
            "INSERT INTO payments (user_id, razorpay_order_id, amount, currency, plan, receipt) VALUES (?, ?, ?, ?, ?, ?)",
            (current_user["id"], order["id"], amount_in_paise, "INR", req.plan, order_data["receipt"])
        )
        conn.commit()
        conn.close()

        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "plan": req.plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

@app.post("/payment/verify")
async def verify_payment(
    req: PaymentVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay not configured")

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": req.razorpay_order_id,
            "razorpay_payment_id": req.razorpay_payment_id,
            "razorpay_signature": req.razorpay_signature
        })

        conn = get_db()
        conn.execute(
            "UPDATE payments SET razorpay_payment_id = ?, razorpay_signature = ?, status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE razorpay_order_id = ?",
            (req.razorpay_payment_id, req.razorpay_signature, req.razorpay_order_id)
        )
        conn.commit()
        payment = conn.execute("SELECT plan FROM payments WHERE razorpay_order_id = ?", (req.razorpay_order_id,)).fetchone()
        conn.close()

        if payment:
            conn = get_db()
            conn.execute("UPDATE users SET plan = ? WHERE id = ?", (payment["plan"], current_user["id"]))
            conn.commit()
            conn.close()

        return {
            "status": "success",
            "message": "Payment verified successfully",
            "plan": payment["plan"] if payment else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")

@app.get("/payment/history")
async def get_payment_history(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT razorpay_order_id, razorpay_payment_id, amount, currency, plan, status, created_at, paid_at FROM payments WHERE user_id = ? ORDER BY created_at DESC",
        (current_user["id"],)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------- ADMIN ----------
@app.get("/admin/grievances")
async def get_grievances(admin_key: str):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, email, subject, message, created_at FROM contacts WHERE subject LIKE 'GRIEVANCE:%' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/admin/download-db")
async def download_db(admin_key: str):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not os.path.exists(DATABASE_URL):
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(DATABASE_URL, filename="lexsarthi.db", media_type="application/octet-stream")

# ---------- DATA RETENTION ----------
def cleanup_expired_data():
    conn = get_db()
    conn.execute("DELETE FROM contacts WHERE created_at < datetime('now', '-12 months')")
    conn.commit()
    conn.close()
    print("✅ Expired data cleaned up.")

@app.on_event("startup")
async def startup_event():
    cleanup_expired_data()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)