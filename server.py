import os
import json
import re
import asyncio
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import pdfplumber
import PyPDF2
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# OpenRouter client
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL = "openrouter/free"          # free tier, auto‑selects best model
FALLBACK_MODEL = "openai/gpt-3.5-turbo"
MAX_TOKENS_PER_CHUNK = 120000
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# -------------------------------
# Helper: chunking
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
# Robust JSON extraction
# -------------------------------
def extract_json_from_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    lines = cleaned.split('\n')
    fixed_lines = []
    in_string = False
    for line in lines:
        new_line = []
        for ch in line:
            if ch == '"' and not in_string:
                in_string = True
            elif ch == '"' and in_string:
                in_string = False
            new_line.append(ch)
        if in_string:
            new_line.append('"')
            in_string = False
        fixed_lines.append(''.join(new_line))
    fixed = '\n'.join(fixed_lines)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}(?=\s*$|\s*\{)', fixed, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return {"error": "Could not parse JSON", "raw": text[:200]}

# -------------------------------
# Generic LLM call with fallback
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
    return response.choices[0].message.content.strip()

async def call_llm_fallback(prompt: str, temperature: float = 0.0) -> str:
    try:
        return await call_llm(prompt, temperature)
    except Exception as e:
        print(f"Primary model failed: {e}, using fallback {FALLBACK_MODEL}")
        response = await client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()

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

# -------------------------------
# Lawyer profile (based on CV)
# -------------------------------
LAWYER_REVIEW = {
    "reviewed_by": "Adv. Pankaj Rustagi",
    "experience": "Advocate with experience in IBC matters, RERA, due diligence, contract review, and legal research. Previously handled Section 7 petitions under IBC before NCLT, due diligence for commercial leases, and cross-border contract reviews.",
    "areas": ["Insolvency & Bankruptcy (IBC)", "Real Estate (RERA)", "Due Diligence", "Contract Negotiation", "Legal Research"],
    "qualification": "LLB from Campus Law Centre, Delhi University",
    "note": "This AI-generated analysis has been reviewed by an advocate. The redlines and missing clause suggestions are based on the lawyer's professional experience. For final legal advice, a full consultation is recommended."
}

def add_lawyer_review(response_data: dict, lawyer_review_flag: bool) -> dict:
    if lawyer_review_flag:
        response_data["lawyer_review"] = {**LAWYER_REVIEW, "review_date": datetime.utcnow().isoformat()}
    return response_data

# ========================
# 1. CONTRACT RISK ANALYSIS
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

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    lawyer_review: bool = Form(False)
):
    file_bytes = await file.read()
    text = await extract_text(file_bytes, file.filename)
    if not text.strip():
        raise HTTPException(400, "No text extracted from PDF.")

    chunks = split_text_with_overlap(text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    results = []
    for i, chunk in enumerate(chunks):
        prompt = CONTRACT_PROMPT + f"\nChunk {i+1}/{len(chunks)}:\n{chunk}"
        raw = await call_llm_fallback(prompt)
        results.append(extract_json_from_text(raw))

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
        score = {"Low":0, "Medium":1, "High":2}.get(risk, 0)
        overall_risk_score = max(overall_risk_score, score)
        if res.get("executive_summary"):
            summaries.append(res["executive_summary"])
    final_risk = ["Low", "Medium", "High"][overall_risk_score]
    final_summary = " ".join(summaries) if summaries else "Analysis complete."

    response = {
        "clause_analysis": list(merged_clauses.values()),
        "missing_clauses": list(merged_missing.values()),
        "overall_risk": final_risk,
        "executive_summary": final_summary
    }
    return add_lawyer_review(response, lawyer_review)

# ========================
# 2. DPDP CHECK
# ========================
DPDP_PROMPT = """You are a DPDP Act compliance expert. Analyze this privacy policy or data processing clause. Provide a JSON report with:
- compliance_score: "High"/"Medium"/"Low"
- violations: list of missing/incorrect provisions (each with "provision", "risk", "redline")
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
    lawyer_review = request.get("lawyer_review", False)
    if not text.strip():
        raise HTTPException(400, "No text provided")
    prompt = DPDP_PROMPT + text
    raw = await call_llm_fallback(prompt)
    response = extract_json_from_text(raw)
    return add_lawyer_review(response, lawyer_review)

# ========================
# 3. LEGAL NOTICE DRAFTING
# ========================
NOTICE_PROMPT = """You are a legal drafting expert. Draft a formal legal notice based on the following information. Return JSON with:
- notice_text: full notice (to, from, subject, body, deadline)
- key_legal_basis: relevant Indian laws (e.g., Contract Act, IBC)
- suggested_action: what the sender should do next
- lawyer_comments: a short paragraph of lawyer's review of the notice (as if a senior advocate)

Return ONLY JSON:
{
  "notice_text": "...",
  "key_legal_basis": "...",
  "suggested_action": "...",
  "lawyer_comments": "..."
}
Details: """

@app.post("/legal-notice")
async def legal_notice(request: dict):
    sender = request.get("sender", "")
    recipient = request.get("recipient", "")
    details = request.get("details", "")
    lawyer_review = request.get("lawyer_review", False)
    prompt = NOTICE_PROMPT + f"Sender: {sender}\nRecipient: {recipient}\nDispute: {details}"
    raw = await call_llm_fallback(prompt, temperature=0.3)
    response = extract_json_from_text(raw)
    return add_lawyer_review(response, lawyer_review)

# ========================
# 4. DUE DILIGENCE (batch)
# ========================
DD_PROMPT = """You are a due diligence expert. Analyze the uploaded documents and return JSON with:
- red_flags: list of high-risk findings (each with "document", "clause", "risk", "action")
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
async def due_diligence(files: List[UploadFile] = File(...), lawyer_review: bool = Form(False)):
    combined = ""
    for f in files:
        content = await f.read()
        txt = await extract_text(content, f.filename)
        combined += f"\n===== {f.filename} =====\n{txt[:2000]}\n"
    prompt = DD_PROMPT + combined[:15000]
    raw = await call_llm_fallback(prompt)
    response = extract_json_from_text(raw)
    return add_lawyer_review(response, lawyer_review)

# ========================
# 5. NDA TRIAGE
# ========================
NDA_PROMPT = """You are an NDA expert. Classify the NDA below. Return JSON:
- risk_level: "Low/Medium/High"
- problematic_clauses: list of clauses that need revision (each with "clause", "reason", "redline")
- executive_summary: one paragraph

Return ONLY JSON:
{
  "risk_level": "...",
  "problematic_clauses": [{"clause": "...", "reason": "...", "redline": "..."}],
  "executive_summary": "..."
}
NDA text: """

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...), lawyer_review: bool = Form(False)):
    content = await file.read()
    text = await extract_text(content, file.filename)
    if not text.strip():
        raise HTTPException(400, "No text extracted")
    prompt = NDA_PROMPT + text[:15000]
    raw = await call_llm_fallback(prompt)
    response = extract_json_from_text(raw)
    return add_lawyer_review(response, lawyer_review)

# ========================
# 6. WEEKLY DIGEST
# ========================
WEEKLY_PROMPT = """Summarise key legal developments in India and globally related to '{topic}'. Return JSON:
{
  "digest": ["point1", "point2", "point3"],
  "sources": ["law", "judgment", "article"],
  "executive_summary": "..."
}
"""

@app.get("/weekly-digest")
async def weekly_digest(q: Optional[str] = None, lawyer_review: bool = False):
    topic = q or "recent legal developments in India"
    prompt = WEEKLY_PROMPT.format(topic=topic)
    raw = await call_llm_fallback(prompt, temperature=0.5)
    response = extract_json_from_text(raw)
    return add_lawyer_review(response, lawyer_review)

# ========================
# 7. CONSENT FORM GENERATOR (includes California Data Broker Act)
# ========================
CONSENT_PROMPT = """You are a data privacy lawyer specializing in the California Data Broker Registry and Delete Act (Title 1.81.5.1, Sections 1798.99.80-1798.99.89). Generate a comprehensive consent form for data collection and processing that complies with this Act, as well as DPDP Act 2025 and GDPR principles.

The consent form must include:
1. Clear identification of the data broker (if applicable) or data controller.
2. Description of personal information collected (including categories listed in Section 1798.99.82(b)(2)(D)-(T): names, email, precise geolocation, biometric data, reproductive health data, etc.).
3. Purpose of collection and sale/sharing to third parties.
4. Consumer's right to deletion via the accessible deletion mechanism (Section 1798.99.86).
5. Right to opt out of sale/sharing (Section 1798.120).
6. Right to correct inaccurate information (Section 1798.106).
7. Right to know what personal information is collected and with whom it is shared (Sections 1798.110, 1798.115).
8. Link to the data broker's privacy policy and deletion mechanism.
9. Statement that data broker will not use dark patterns (Section 1798.99.82(b)(2)(V)(ii)).
10. Notice of potential administrative fines for non-compliance (Section 1798.99.82(c)-(d)).
11. Information about the Data Brokers' Registry Fund (Section 1798.99.81).

Return JSON:
{{
  "form_title": "Consent Form under California Data Broker Registry and Delete Act",
  "consent_text": "Full consent form text in plain English, including all required disclosures and a checkbox line for user consent.",
  "required_disclosures": ["List of mandatory statements as per the Act", "e.g., right to deletion every 45 days", "right to opt out", "no dark patterns"],
  "data_broker_registration_info": {{
    "registration_required": true/false,
    "fee_info": "if applicable",
    "audit_requirement": "every 3 years from 2028"
  }}
}}

Purpose: {purpose}
Data collected: {data}
"""

@app.post("/consent-form")
async def consent_form(request: dict):
    purpose = request.get("purpose", "")
    data_collected = request.get("data_collected", "")
    lawyer_review = request.get("lawyer_review", False)
    prompt = CONSENT_PROMPT.format(purpose=purpose, data=data_collected)
    raw = await call_llm_fallback(prompt, temperature=0.3)
    response = extract_json_from_text(raw)
    return add_lawyer_review(response, lawyer_review)

# ========================
# Health check
# ========================
@app.get("/health")
async def health():
    return {"status": "ok"}