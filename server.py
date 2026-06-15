import os
import shutil
import time
import hmac
import hashlib
import asyncio
import zipfile
import io
import json
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings, Document
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_parse import LlamaParse
from pypdf import PdfReader
import razorpay

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ---------- LLM (Groq) – using supported model ----------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set")
Settings.llm = OpenAILike(
    model="llama-3.3-70b-versatile",   # changed from mixtral
    api_key=api_key,
    api_base="https://api.groq.com/openai/v1",
    is_chat_model=True,
    temperature=0.1,
)

# ---------- Embeddings ----------
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# ---------- LlamaParse parser ----------
parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown",
    verbose=True,
)

# ---------- Razorpay client ----------
razorpay_key_id = os.getenv("RAZORPAY_KEY_ID")
razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if not razorpay_key_id or not razorpay_key_secret:
    print("Warning: Razorpay keys not set – /create-order will not work")
else:
    razorpay_client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))

# ---------- Load permanent index ----------
index = None
if os.path.exists("legal_docs") and any(os.scandir("legal_docs")):
    documents = []
    for file in os.listdir("legal_docs"):
        if file.lower().endswith(".pdf"):
            file_path = os.path.join("legal_docs", file)
            docs = parser.load_data(file_path)
            documents.extend(docs)
    if documents:
        index = VectorStoreIndex.from_documents(documents)
        print(f"Loaded {len(documents)} document chunks")
    else:
        print("No valid PDFs found in legal_docs/")
else:
    print("No PDFs found in legal_docs/")

# ---------- Health ----------
@app.get("/health")
async def health():
    return {"status": "ok", "docs_loaded": index is not None}

# ---------- Query permanent index ----------
@app.get("/query")
async def query(q: str = Query(...)):
    if index is None:
        return {"query": q, "response": "No legal documents loaded."}
    try:
        response = index.as_query_engine().query(q)
        answer = response.response if hasattr(response, 'response') else str(response)
        return {"query": q, "response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Contract risk analysis (polished corporate lawyer) ----------
import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional

import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fastapi import HTTPException
from groq import RateLimitError

# Assume you already have these from your current server.py
from llama_index.core import SimpleDirectoryReader
from llama_parse import LlamaParse
from groq import AsyncGroq

# -------------------------------
# Constants & Configuration
# -------------------------------
GROQ_MODEL_PRIMARY = "llama-3.3-70b-versatile"   # 8k context
GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"     # 8k context, faster/cheaper
MAX_TOKENS_PER_CHUNK = 6000   # leaves 2000 tokens for prompt + response
OVERLAP_TOKENS = 500           # overlap to avoid cutting clauses
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")  # close enough for llama

logger = logging.getLogger(__name__)

# -------------------------------
# Helper: Split text with overlap
# -------------------------------
def split_text_with_overlap(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """
    Split text into chunks of approx `max_tokens` tokens, with `overlap_tokens`
    overlap between consecutive chunks. Tries to cut at sentence boundaries.
    """
    tokens = TOKEN_ENCODER.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = TOKEN_ENCODER.decode(chunk_tokens)

        # Try to cut at a sentence boundary (period, newline, etc.) for readability
        # but don't enforce strictly – the LLM can handle mid‑sentence.
        chunks.append(chunk_text)

        # Move start, but go back by overlap_tokens (unless at the end)
        if end >= len(tokens):
            break
        start = end - overlap_tokens

    return chunks

# -------------------------------
# Stricter clause‑focused prompt
# -------------------------------
def build_analysis_prompt(chunk_text: str, chunk_index: int, total_chunks: int) -> str:
    return f"""
You are an expert Indian contract analyst. Analyze the following **part of a contract** (chunk {chunk_index+1} of {total_chunks}).

## INSTRUCTIONS (STRICT – FOLLOW EXACTLY)

1. **Extract EVERY clause** that appears in this chunk. For each clause, provide:
   - `clause_number`: string (e.g., "4.2", "XII(c)", "Indemnity")
   - `title`: short clause name (e.g., "Indemnification", "Termination")
   - `risk_level`: "Low", "Medium", "High"
   - `legal_basis`: specific section of Indian law (e.g., "Section 124 of Indian Contract Act, 1872", "Section 22 of DPDP Act, 2025", "Section 9 of IBC, 2016")
   - `reason`: detailed explanation (2-3 sentences) why this risk level applies.
   - `redline`: exact suggested replacement text for the problematic part (or "No change" if low risk).

2. **If a clause is split across multiple chunks**, analyse only the portion visible. We will merge later.

3. **For missing essential clauses** (even if not present in this chunk, but standard for Indian contracts), add them to `missing_clauses` array. For each missing clause, include:
   - `title`: clause name
   - `risk_level`: always "High"
   - `legal_basis`: relevant Indian law
   - `reason`: why it is required
   - `proposed_clause_text`: draft wording as it should appear in the contract.

Essential clauses to check: limitation of liability, indemnity, termination for convenience, data protection (DPDP Act compliance), non-compete, non-solicit, arbitration (with Indian seat), governing law (India), force majeure, notice, entire agreement, amendment, severability, waiver, assignment.

4. **Overall risk** for this chunk: "Low", "Medium", or "High" based on the worst clause in this chunk.

5. **Executive summary** (one paragraph) highlighting the most critical risks in this chunk.

## OUTPUT FORMAT – VALID JSON ONLY, NO MARKDOWN, NO EXTRA TEXT.

{{
  "clause_analysis": [
    {{
      "clause_number": "...",
      "title": "...",
      "risk_level": "...",
      "legal_basis": "...",
      "reason": "...",
      "redline": "..."
    }}
  ],
  "missing_clauses": [
    {{
      "title": "...",
      "risk_level": "High",
      "legal_basis": "...",
      "reason": "...",
      "proposed_clause_text": "..."
    }}
  ],
  "overall_risk": "...",
  "executive_summary": "..."
}}

## CONTRACT CHUNK (START)
{chunk_text}
## CONTRACT CHUNK (END)
"""

# -------------------------------
# Retry logic for rate limits + fallback model
# -------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(RateLimitError),
    reraise=True
)
async def call_groq_with_backoff(client: AsyncGroq, model: str, prompt: str) -> str:
    """Call Groq API with exponential backoff on rate limit errors."""
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}  # forces JSON output
    )
    return response.choices[0].message.content

async def analyze_chunk(client: AsyncGroq, chunk_text: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
    """Analyze a single chunk with fallback model if primary fails due to rate limits."""
    prompt = build_analysis_prompt(chunk_text, chunk_index, total_chunks)
    try:
        result_json = await call_groq_with_backoff(client, GROQ_MODEL_PRIMARY, prompt)
    except RateLimitError:
        logger.warning(f"Rate limit on primary model, switching to fallback for chunk {chunk_index}")
        result_json = await call_groq_with_backoff(client, GROQ_MODEL_FALLBACK, prompt)
    except Exception as e:
        logger.error(f"Chunk {chunk_index} failed: {e}")
        # Return empty structure so merge can still proceed
        return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "High", "executive_summary": f"Analysis failed for chunk {chunk_index}"}
    
    try:
        return json.loads(result_json)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from chunk {chunk_index}: {result_json[:200]}")
        return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "High", "executive_summary": f"JSON parse error in chunk {chunk_index}"}

# -------------------------------
# Merge results from multiple chunks
# -------------------------------
def merge_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine clause_analysis, missing_clauses, overall_risk, and executive_summary
    from multiple chunks.
    """
    merged_clauses = {}   # key = clause_number or title (fallback)
    merged_missing = {}   # key = missing clause title
    overall_risk_levels = {"Low": 0, "Medium": 1, "High": 2}
    max_risk_score = 0
    summaries = []

    for res in results:
        # Merge clauses: use clause_number as primary key, else title
        for clause in res.get("clause_analysis", []):
            key = clause.get("clause_number") or clause.get("title")
            if not key:
                key = f"unknown_{id(clause)}"
            # Keep the most detailed version (prefer one with non-empty redline or longer reason)
            existing = merged_clauses.get(key)
            if not existing or (clause.get("redline") and not existing.get("redline")):
                merged_clauses[key] = clause
            elif len(clause.get("reason", "")) > len(existing.get("reason", "")):
                merged_clauses[key] = clause

        # Merge missing clauses
        for missing in res.get("missing_clauses", []):
            title = missing.get("title")
            if title and title not in merged_missing:
                merged_missing[title] = missing

        # Track highest risk
        risk = res.get("overall_risk", "Low")
        risk_score = overall_risk_levels.get(risk, 0)
        if risk_score > max_risk_score:
            max_risk_score = risk_score

        # Collect summaries
        if res.get("executive_summary"):
            summaries.append(res["executive_summary"])

    # Determine final overall risk
    risk_map_rev = {0: "Low", 1: "Medium", 2: "High"}
    final_risk = risk_map_rev[max_risk_score]

    # Combine summaries into one paragraph
    final_summary = " ".join(summaries) if summaries else "No executive summary available."

    return {
        "clause_analysis": list(merged_clauses.values()),
        "missing_clauses": list(merged_missing.values()),
        "overall_risk": final_risk,
        "executive_summary": final_summary
    }

# -------------------------------
# New /analyze endpoint
# -------------------------------
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    """
    Enhanced contract analysis with multi‑chunk processing, clause‑aware splitting,
    and rate‑limit fallback.
    """
    # 1. Parse PDF using LlamaParse (as in your existing code)
    try:
        # You already have LlamaParse set up – adapt this to your current parsing logic
        parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="text")
        documents = await asyncio.to_thread(parser.load_data, await file.read())
        contract_text = "\n".join([doc.text for doc in documents])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF parsing failed: {str(e)}")

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    # 2. Split into overlapping token chunks
    chunks = split_text_with_overlap(contract_text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    logger.info(f"Split contract into {len(chunks)} chunks for analysis.")

    # 3. Initialize Groq client (use your existing client creation)
    groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    # 4. Analyze each chunk concurrently (with concurrency limit to avoid rate limits)
    semaphore = asyncio.Semaphore(3)  # max 3 concurrent calls

    async def analyze_with_semaphore(chunk, idx):
        async with semaphore:
            return await analyze_chunk(groq_client, chunk, idx, len(chunks))

    tasks = [analyze_with_semaphore(chunk, i) for i, chunk in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks)

    # 5. Merge results
    final_report = merge_results(chunk_results)

    # 6. Return final JSON
    return final_report
@app.post("/api/create-order")
async def create_order(amount: int = 500):
    if not razorpay_key_id or not razorpay_key_secret:
        raise HTTPException(500, detail="Razorpay not configured")
    try:
        order_data = {
            "amount": amount * 100,
            "currency": "INR",
            "payment_capture": 1,
            "receipt": f"order_rcpt_{int(time.time())}"
        }
        order = razorpay_client.order.create(data=order_data)
        return {"order_id": order["id"], "amount": amount, "currency": "INR"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Payment verification ----------
@app.post("/api/verify-payment")
async def verify_payment(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not razorpay_webhook_secret:
        raise HTTPException(500, detail="Webhook secret not set")
    expected = hmac.new(
        razorpay_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    return {"status": "success"}

# ========== Additional Agents ==========
@app.post("/dpdp-check")
async def dpdp_check(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        docs = await asyncio.to_thread(parser.load_data, temp_path)
        if not docs:
            reader = PdfReader(temp_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            docs = [Document(text=text)]
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()
        prompt = (
            "You are a DPDP Act compliance auditor. Analyze the given document against the Digital Personal Data Protection Act 2023. "
            "Return a JSON with:\n"
            "- compliance_score: 0-100\n"
            "- missing_clauses: list of DPDP requirements not met\n"
            "- observations: brief remarks"
        )
        response = engine.query(prompt)
        return {"filename": file.filename, "report": str(response)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/legal-notice")
async def legal_notice(request: Request):
    data = await request.json()
    parties = data.get("parties", [])
    facts = data.get("facts", "")
    law = data.get("applicable_law", "Indian Contract Act, 1872")
    prompt = f"""Generate a formal legal notice under {law}.
    Parties: {', '.join(parties) if parties else 'Not specified'}.
    Facts: {facts}
    Format as a legal notice with:
    - Subject line
    - Date
    - Recipient details (placeholders)
    - Body explaining breach/demand
    - Deadline for compliance
    - Signature block (placeholder)
    Do not include advice or commentary."""
    response = Settings.llm.complete(prompt)
    return {"notice": response.text}

@app.post("/due-diligence")
async def due_diligence(zip_file: UploadFile = File(...)):
    contents = await zip_file.read()
    results = []
    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        for name in z.namelist():
            if name.lower().endswith('.pdf'):
                results.append({"file": name, "risk": "pending review"})
    return {"results": results}

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        docs = await asyncio.to_thread(parser.load_data, temp_path)
        if not docs:
            reader = PdfReader(temp_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            docs = [Document(text=text)]
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()
        prompt = "Classify this NDA as green (low risk), amber (medium risk), or red (high risk) based on Indian contract law. Return only the word."
        response = engine.query(prompt)
        answer = response.response if hasattr(response, 'response') else str(response)
        return {"filename": file.filename, "risk_level": answer.strip()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/weekly-digest")
async def weekly_digest():
    if index is None:
        raise HTTPException(503, detail="Legal index not loaded. Please add PDFs to legal_docs/.")
    queries = [
        "What are the latest amendments to the DPDP Act in the past month?",
        "Recent changes in the Indian Contract Act, 1872",
        "Updates to the Insolvency and Bankruptcy Code (IBC)",
        "New rules or notifications under the Companies Act, 2013",
        "Recent judgments or regulatory changes affecting contract law in India"
    ]
    digest = []
    for q in queries:
        try:
            response = index.as_query_engine().query(q)
            answer = response.response if hasattr(response, 'response') else str(response)
            digest.append({"topic": q, "summary": answer})
        except Exception as e:
            digest.append({"topic": q, "error": str(e)})
    formatted = "# Weekly Regulatory Digest\n\n"
    for item in digest:
        formatted += f"## {item['topic']}\n"
        if "summary" in item:
            formatted += f"{item['summary']}\n\n"
        else:
            formatted += f"Error: {item['error']}\n\n"
    return {"digest": formatted}

@app.post("/consent-form")
async def consent_form(request: Request):
    data = await request.json()
    business_name = data.get("business_name", "Your Organization")
    purpose = data.get("purpose", "Service provision")
    data_types = data.get("data_types", ["name", "email", "phone"])
    retention_days = data.get("retention_days", 180)
    prompt = f"""
You are a legal document drafter. Generate a **Consent Form** under the Digital Personal Data Protection Act (DPDP Act), 2023 (India).  
The form must include:
- Header: "Consent Form – DPDP Act, 2023"
- Business name: {business_name}
- Purpose of data collection: {purpose}
- Types of personal data collected: {', '.join(data_types)}
- Retention period: {retention_days} days
- Data principal rights (access, correction, erasure, grievance)
- Withdrawal of consent notice
- Grievance redressal contact (placeholder)
- Signature line (date and name)

Format the output as clean HTML or plain text with clear headings.
"""
    response = Settings.llm.complete(prompt)
    form_html = response.text if hasattr(response, 'text') else str(response)
    return {"consent_form": form_html}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)