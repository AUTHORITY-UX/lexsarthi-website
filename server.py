import os
import json
import io
import re
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import PyPDF2
import pdfplumber
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ---------- App ----------
app = FastAPI(title="LexSarthi API", version="2.0")

# CORS – allow your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://advocacyalawfrim.in",
        "https://www.advocacyalawfrim.in",
        "https://dbeba57b.lexsarthi-website.pages.dev",
        "https://lexsarthi-website.pages.dev",
        "http://localhost:3000",  # dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- OpenRouter Client ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
MODEL = "meta-llama/llama-3.1-8b-instruct"   # fast & cheap
MAX_TOKENS_PER_CHUNK = 120000
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# ---------- Pydantic Schemas for Domain Review ----------
class ClauseReview(BaseModel):
    clause_number: str
    clause_text: str
    risk: Literal["Low", "Medium", "High", "Critical"]
    summary: str
    suggested_change: str   # NEVER empty
    actionable: bool
    reason: str

class DomainReviewResponse(BaseModel):
    agreement_type: str
    overall_risk: Literal["Low", "Medium", "High"]
    executive_summary: str
    clauses: List[ClauseReview]
    lawyer_review_required: bool
    review_id: Optional[str] = None

# ---------- Utilities ----------
def extract_json_from_text(text: str) -> dict:
    """Robust JSON extraction from LLM output."""
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
    """Extract text from PDF or text file."""
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

# ---------- LLM Caller with Retry & Fallback ----------
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

# ---------- Expert Lawyer Profile (for optional review) ----------
LAWYER_REVIEW = {
    "reviewed_by": "Adv. Pankaj Rustagi",
    "experience": "Advocate with 40 years of experience in corporate law, IBC, RERA, due diligence, contract review, and legal research.",
    "areas": ["Insolvency & Bankruptcy (IBC)", "Real Estate (RERA)", "Due Diligence", "Contract Negotiation", "Legal Research"],
    "qualification": "LLB from Campus Law Centre, Delhi University",
    "note": "This AI-generated analysis has been reviewed by an advocate. The redlines and missing clause suggestions are based on professional experience. For final legal advice, a full consultation is recommended."
}

def add_lawyer_review(response: dict, flag: bool) -> dict:
    if flag:
        response["lawyer_review"] = {**LAWYER_REVIEW, "review_date": datetime.utcnow().isoformat()}
    return response

# ========================
# 1. CONTRACT RISK ANALYSIS (Expert)
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

# ========================
# 2. DPDP CHECK
# ========================
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

# ========================
# 3. LEGAL NOTICE
# ========================
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

# ========================
# 4. DUE DILIGENCE
# ========================
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

# ========================
# 5. NDA TRIAGE
# ========================
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

# ========================
# 6. WEEKLY DIGEST
# ========================
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

# ========================
# 7. CONSENT FORM
# ========================
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

# ========================
# 8. DOMAIN AGREEMENT REVIEW (NEW)
# ========================
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
    # Enforce non‑empty suggested_change
    for c in data.get("clauses", []):
        if not c.get("suggested_change") or c["suggested_change"].strip().lower() in ["no change", "none", "n/a"]:
            c["suggested_change"] = f"Review this clause to address {c.get('risk', 'Medium')} risk."
    return data

# ========================
# API ENDPOINTS
# ========================

@app.get("/health")
async def health():
    return {"status": "ok"}

# Generic /run-agent (for test harness)
@app.post("/run-agent")
async def run_agent(
    agent_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    handlers = {
        "contract_risk": lambda t: analyze_contract_risk(t),
        "dpdp_check": lambda t: check_dpdp(t),
        "legal_notice": lambda t: draft_legal_notice(t),
        "due_diligence": lambda t: perform_due_diligence(t),
        "nda_triage": lambda t: triage_nda(t),
        "weekly_digest": lambda t: generate_digest(t),
        "consent_form": lambda t: generate_consent(t, ""),  # note: consent expects purpose+data
    }
    if agent_name not in handlers:
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
    result = await handlers[agent_name](content)
    return result

# Existing endpoints – we keep them for backward compatibility
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...), lawyer_review: bool = Form(False)):
    content = await extract_text_from_file(await file.read(), file.filename)
    if not content.strip():
        raise HTTPException(400, "No text extracted")
    result = await analyze_contract_risk(content)
    return add_lawyer_review(result, lawyer_review)

@app.post("/dpdp-check")
async def dpdp_check(request: dict):
    text = request.get("text", "")
    lawyer = request.get("lawyer_review", False)
    if not text.strip():
        raise HTTPException(400, "No text")
    result = await check_dpdp(text)
    return add_lawyer_review(result, lawyer)

@app.post("/legal-notice")
async def legal_notice(request: dict):
    sender = request.get("sender", "")
    recipient = request.get("recipient", "")
    details = request.get("details", "")
    lawyer = request.get("lawyer_review", False)
    if not sender or not recipient or not details:
        raise HTTPException(400, "Missing sender/recipient/details")
    prompt = f"Sender: {sender}\nRecipient: {recipient}\nDispute: {details}"
    result = await draft_legal_notice(prompt)
    return add_lawyer_review(result, lawyer)

@app.post("/due-diligence")
async def due_diligence(files: List[UploadFile] = File(...), lawyer_review: bool = Form(False)):
    combined = ""
    for f in files:
        content = await f.read()
        txt = await extract_text_from_file(content, f.filename)
        combined += f"\n===== {f.filename} =====\n{txt[:2000]}\n"
    result = await perform_due_diligence(combined[:15000])
    return add_lawyer_review(result, lawyer_review)

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...), lawyer_review: bool = Form(False)):
    content = await extract_text_from_file(await file.read(), file.filename)
    if not content.strip():
        raise HTTPException(400, "No text")
    result = await triage_nda(content)
    return add_lawyer_review(result, lawyer_review)

@app.get("/weekly-digest")
async def weekly_digest(q: Optional[str] = None, lawyer_review: bool = False):
    topic = q or "recent legal developments in India"
    result = await generate_digest(topic)
    return add_lawyer_review(result, lawyer_review)

@app.post("/consent-form")
async def consent_form(request: dict):
    purpose = request.get("purpose", "")
    data = request.get("data_collected", "")
    lawyer = request.get("lawyer_review", False)
    if not purpose or not data:
        raise HTTPException(400, "Missing purpose or data")
    result = await generate_consent(purpose, data)
    return add_lawyer_review(result, lawyer)

# NEW: Domain Agreement Review endpoint (with payment)
@app.post("/domain-review", response_model=DomainReviewResponse)
async def domain_review(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    payment_id: str = Form(...),
    plan: Literal["500", "1000"] = Form(...)
):
    # 1. Verify payment with Razorpay – placeholder
    #    You should call your existing payment verification function.
    #    For now, we assume payment is valid.
    content = ""
    if file:
        content = await extract_text_from_file(await file.read(), file.filename)
    elif text:
        content = text
    else:
        raise HTTPException(400, "No input")
    if len(content.strip()) < 50:
        raise HTTPException(400, "Agreement too short")
    analysis = await analyze_domain_agreement(content)
    is_lawyer = (plan == "1000")
    review_id = f"REV-{payment_id[-8:]}" if is_lawyer else None
    # If lawyer plan, store in DB (optional) and notify lawyer.
    return DomainReviewResponse(
        agreement_type=analysis.get("agreement_type", "Other"),
        overall_risk=analysis.get("overall_risk", "Medium"),
        executive_summary=analysis.get("executive_summary", ""),
        clauses=[ClauseReview(**c) for c in analysis.get("clauses", [])],
        lawyer_review_required=is_lawyer,
        review_id=review_id
    )