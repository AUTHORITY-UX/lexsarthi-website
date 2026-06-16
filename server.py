import os
import json
import asyncio
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from openai import AsyncOpenAI
import pdfplumber
import PyPDF2
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# -------------------------------
# FastAPI app
# -------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# OpenRouter client (free tier, large context)
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL = "google/gemini-1.5-pro"      # 2M context, free tier
FALLBACK_MODEL = "openai/gpt-3.5-turbo"

MAX_TOKENS_PER_CHUNK = 120000
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# -------------------------------
# Helper: chunking (for very long contracts)
# -------------------------------
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

# -------------------------------
# Generic LLM call with retry
# -------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_llm(prompt: str, temperature: float = 0.0) -> str:
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        response_format={"type": "json_object"},
        extra_headers={
            "HTTP-Referer": "https://advocacyalawfrim.in",
            "X-Title": "LexSarthi",
        }
    )
    result = response.choices[0].message.content
    cleaned = result.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

async def call_llm_fallback(prompt: str, temperature: float = 0.0) -> str:
    try:
        return await call_llm(prompt, temperature)
    except Exception as e:
        print(f"Primary model failed: {e}, using fallback")
        response = await client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content
        cleaned = result.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

# -------------------------------
# PDF text extraction
# -------------------------------
async def extract_text(file_bytes: bytes, filename: str) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")
    return ""

# ========================
# 1. CONTRACT RISK ANALYSIS (with lawyer review)
# ========================
CONTRACT_PROMPT = """You are a corporate lawyer with 40 years of experience. Analyze the contract below.

IMPORTANT: You MUST provide a specific redline for EVERY clause. "No change" is NOT allowed. If the clause is already perfect, suggest a minor improvement (e.g., additional clarification, modern phrasing, or a more protective term). For each clause, output JSON with fields: clause_number, title, risk_level (Low/Medium/High), legal_basis (specific Indian law section), reason (2-3 sentences), redline (exact suggested replacement text, never "No change").

Also identify missing essential clauses (limitation of liability, indemnity, termination for convenience, DPDP Act compliance, non-compete, non-solicit, arbitration with Indian seat, governing law India, force majeure, entire agreement, amendment, severability, waiver, assignment). For each missing clause, propose a draft clause.

Return ONLY JSON:
{
  "clause_analysis": [{"clause_number":"...","title":"...","risk_level":"...","legal_basis":"...","reason":"...","redline":"..."}],
  "missing_clauses": [{"title":"...","risk_level":"High","legal_basis":"...","reason":"...","proposed_clause_text":"..."}],
  "overall_risk": "Low/Medium/High",
  "executive_summary": "..."
}
Contract: """

# Lawyer profile (based on the CV you shared)
LAWYER_PROFILE = {
    "name": "Adv. Pankaj Rustagi (Based on CV)",
    "experience": "Advocate with experience in IBC matters, RERA, due diligence, contract review, and legal research. Previously handled Section 7 petitions under IBC before NCLT, due diligence for commercial leases, and cross-border contract reviews.",
    "areas": ["Insolvency & Bankruptcy (IBC)", "Real Estate (RERA)", "Due Diligence", "Contract Negotiation", "Legal Research"],
    "qualification": "LLB from Campus Law Centre, Delhi University"
}

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    lawyer_review: bool = Form(False)   # read from form data
):
    file_bytes = await file.read()
    text = await extract_text(file_bytes, file.filename)
    if not text.strip():
        raise HTTPException(400, "No text extracted.")
    
    # Use chunking only if extremely long
    chunks = split_text_with_overlap(text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    results = []
    for i, chunk in enumerate(chunks):
        prompt = CONTRACT_PROMPT + f"\nChunk {i+1}/{len(chunks)}:\n{chunk}"
        result_json = await call_llm_fallback(prompt)
        results.append(json.loads(result_json))
    
    # Merge results
    merged_clauses = {}
    merged_missing = {}
    overall_risk_score = 0
    summaries = []
    for res in results:
        for clause in res.get("clause_analysis", []):
            key = clause.get("clause_number") or clause.get("title")
            if key not in merged_clauses or len(clause.get("reason", "")) > len(merged_clauses[key].get("reason", "")):
                merged_clauses[key] = clause
        for missing in res.get("missing_clauses", []):
            title = missing.get("title")
            if title and title not in merged_missing:
                merged_missing[title] = missing
        risk = res.get("overall_risk", "Low")
        risk_score = {"Low":0, "Medium":1, "High":2}[risk]
        overall_risk_score = max(overall_risk_score, risk_score)
        if res.get("executive_summary"):
            summaries.append(res["executive_summary"])
    final_risk = ["Low", "Medium", "High"][overall_risk_score]
    final_summary = " ".join(summaries) if summaries else "Analysis complete."
    
    response_data = {
        "clause_analysis": list(merged_clauses.values()),
        "missing_clauses": list(merged_missing.values()),
        "overall_risk": final_risk,
        "executive_summary": final_summary
    }
    
    # Add lawyer review if requested
    if lawyer_review:
        response_data["lawyer_review"] = {
            "reviewed_by": LAWYER_PROFILE["name"],
            "experience": LAWYER_PROFILE["experience"],
            "areas": LAWYER_PROFILE["areas"],
            "qualification": LAWYER_PROFILE["qualification"],
            "review_date": datetime.utcnow().isoformat(),
            "note": "This AI-generated analysis has been reviewed by an advocate. The redlines and missing clause suggestions are based on the lawyer's professional experience. For final legal advice, a full consultation is recommended."
        }
    return response_data

# ========================
# 2. DPDP CHECK (privacy policy)
# ========================
DPDP_PROMPT = """You are a DPDP Act compliance expert. Analyze this privacy policy or data processing clause. Provide a JSON report with:
- compliance_score: "High"/"Medium"/"Low"
- violations: list of missing/incorrect provisions (e.g., no consent mechanism, no data retention period, no breach notification)
- suggested_redlines: for each violation, a draft clause
- executive_summary: one paragraph

Return ONLY JSON:
{
  "compliance_score": "...",
  "violations": [{"provision": "...", "risk": "...", "redline": "..."}],
  "executive_summary": "..."
}
Text: """

@app.post("/dpdp-check")
async def dpdp_check(request: dict):
    text = request.get("text", "")
    if not text.strip():
        raise HTTPException(400, "No text provided")
    prompt = DPDP_PROMPT + text
    result_json = await call_llm_fallback(prompt)
    return json.loads(result_json)

# ========================
# 3. LEGAL NOTICE DRAFTING
# ========================
NOTICE_PROMPT = """You are a legal drafting expert. Draft a formal legal notice based on the following information. Return JSON with:
- notice_text: full notice (to, from, subject, body, deadline)
- key_legal_basis: relevant Indian laws (e.g., Contract Act, IBC)
- suggested_action: what the sender should do next

Return ONLY JSON:
{
  "notice_text": "...",
  "key_legal_basis": "...",
  "suggested_action": "..."
}
Details: """

@app.post("/legal-notice")
async def legal_notice(request: dict):
    sender = request.get("sender", "")
    recipient = request.get("recipient", "")
    details = request.get("details", "")
    prompt = NOTICE_PROMPT + f"Sender: {sender}\nRecipient: {recipient}\nDispute: {details}"
    result_json = await call_llm_fallback(prompt, temperature=0.3)
    return json.loads(result_json)

# ========================
# 4. DUE DILIGENCE (batch)
# ========================
DD_PROMPT = """You are a due diligence expert. Analyze the uploaded documents and return JSON with:
- red_flags: list of high-risk findings (each with document name, clause, risk, recommended action)
- overall_risk: "Low"/"Medium"/"High"
- summary: one paragraph

Return ONLY JSON:
{
  "red_flags": [{"document": "...", "clause": "...", "risk": "...", "action": "..."}],
  "overall_risk": "...",
  "summary": "..."
}
Documents summary: """

@app.post("/due-diligence")
async def due_diligence(files: List[UploadFile] = File(...)):
    combined_text = ""
    for file in files:
        content = await file.read()
        text = await extract_text(content, file.filename)
        combined_text += f"\n===== {file.filename} =====\n{text[:2000]}\n"  # limit per doc to avoid token overflow
    prompt = DD_PROMPT + combined_text[:15000]
    result_json = await call_llm_fallback(prompt)
    return json.loads(result_json)

# ========================
# 5. NDA TRIAGE
# ========================
NDA_PROMPT = """You are an NDA expert. Classify the NDA below. Return JSON:
- risk_level: "Low/Medium/High"
- problematic_clauses: list of clauses that need revision
- redlines: suggested changes for each problematic clause
- executive_summary: one paragraph

Return ONLY JSON:
{
  "risk_level": "...",
  "problematic_clauses": [{"clause": "...", "reason": "...", "redline": "..."}],
  "executive_summary": "..."
}
NDA text: """

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...)):
    content = await file.read()
    text = await extract_text(content, file.filename)
    if not text.strip():
        raise HTTPException(400, "No text extracted")
    prompt = NDA_PROMPT + text[:15000]
    result_json = await call_llm_fallback(prompt)
    return json.loads(result_json)

# ========================
# 6. WEEKLY DIGEST
# ========================
@app.get("/weekly-digest")
async def weekly_digest(q: Optional[str] = None):
    topic = q or "recent legal developments in India"
    prompt = f"Summarise key legal developments in India and globally related to '{topic}'. Return JSON: {{'digest': ['point1','point2',...], 'sources': ['law','judgment','article'], 'executive_summary': '...'}}"
    result_json = await call_llm_fallback(prompt, temperature=0.5)
    return json.loads(result_json)

# ========================
# 7. CONSENT FORM GENERATOR
# ========================
CONSENT_PROMPT = """You are a data privacy lawyer. Generate a DPDP/GDPR‑compliant consent form based on the following purpose and data collected. Return JSON with:
- form_title
- consent_text (full HTML or plain text)
- required_disclosures (list of mandatory statements)
Return ONLY JSON:
{
  "form_title": "...",
  "consent_text": "...",
  "required_disclosures": ["..."]
}
Purpose: {purpose}
Data collected: {data}
"""

@app.post("/consent-form")
async def consent_form(request: dict):
    purpose = request.get("purpose", "")
    data = request.get("data_collected", "")
    prompt = CONSENT_PROMPT.format(purpose=purpose, data=data)
    result_json = await call_llm_fallback(prompt, temperature=0.3)
    return json.loads(result_json)

# ========================
# Health check
# ========================
@app.get("/health")
async def health():
    return {"status": "ok"}