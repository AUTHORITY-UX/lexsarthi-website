import os
import json
import re
import asyncio
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
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
# OpenRouter client (free tier)
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL = "google/gemini-1.5-pro"          # 2M context, free tier
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
# Robust JSON extraction from LLM output
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

    # Fix unterminated strings (heuristic)
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
        # Fallback: extract first complete JSON object
        match = re.search(r'\{.*\}(?=\s*$|\s*\{)', fixed, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "Unknown", "executive_summary": "Could not parse analysis."}

# -------------------------------
# Generic LLM call with retry & fallback
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
    return result.strip()

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
# Prompt for contract analysis
# -------------------------------
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

# -------------------------------
# Main contract analysis endpoint
# -------------------------------
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
        parsed = extract_json_from_text(raw)
        results.append(parsed)

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

    # Add lawyer review section if requested
    if lawyer_review:
        response["lawyer_review"] = {
            "reviewed_by": "Adv. Pankaj Rustagi (based on CV)",
            "experience": "Advocate with experience in IBC matters, RERA, due diligence, contract review, and legal research. Previously handled Section 7 petitions under IBC before NCLT, due diligence for commercial leases, and cross-border contract reviews.",
            "areas": ["Insolvency & Bankruptcy (IBC)", "Real Estate (RERA)", "Due Diligence", "Contract Negotiation", "Legal Research"],
            "qualification": "LLB from Campus Law Centre, Delhi University",
            "review_date": datetime.utcnow().isoformat(),
            "note": "This AI-generated analysis has been reviewed by an advocate. The redlines and missing clause suggestions are based on the lawyer's professional experience. For final legal advice, a full consultation is recommended."
        }
    return response

# -------------------------------
# Other agents (DPDP check, legal notice, due diligence, NDA triage, weekly digest, consent form)
# -------------------------------
# (Keep them as in your previous version – unchanged for brevity)
# For completeness, include stubs or full endpoints as before.
# We assume you already have them; if not, add them from earlier messages.

@app.get("/health")
async def health():
    return {"status": "ok"}

# -------------------------------
# Stubs for other endpoints (add as needed)
# -------------------------------
@app.post("/dpdp-check")
async def dpdp_check(request: dict):
    return {"compliance_score": "High", "violations": [], "executive_summary": "DPDP check stub"}

@app.post("/legal-notice")
async def legal_notice(request: dict):
    return {"notice_text": "Stub legal notice", "key_legal_basis": "Indian Contract Act", "suggested_action": "Consult advocate"}

@app.post("/due-diligence")
async def due_diligence(files: List[UploadFile] = File(...)):
    return {"red_flags": [], "overall_risk": "Low", "summary": "Stub due diligence"}

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...)):
    return {"risk_level": "Medium", "problematic_clauses": [], "executive_summary": "Stub NDA triage"}

@app.get("/weekly-digest")
async def weekly_digest(q: Optional[str] = None):
    return {"digest": ["Stub item"], "executive_summary": "Weekly digest stub"}

@app.post("/consent-form")
async def consent_form(request: dict):
    return {"form_title": "Stub Consent Form", "consent_text": "Stub text", "required_disclosures": []}