import os
import asyncio
import json
import logging
import io
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from llama_parse import LlamaParse
from groq import AsyncGroq, RateLimitError
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pdfplumber
import PyPDF2

# -------------------------------
# Configuration
# -------------------------------
GROQ_MODEL_PRIMARY = "llama-3.3-70b-versatile"   # 8k context
GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"     # 8k context
MAX_TOKENS_PER_CHUNK = 6000   # leaves 2000 tokens for prompt + response
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")  # close enough for Llama

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

# -------------------------------
# Helper: split text with overlap
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
# Strict clause‑focused prompt
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
# Retry + fallback for Groq
# -------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(RateLimitError),
    reraise=True
)
async def call_groq_with_backoff(client: AsyncGroq, model: str, prompt: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def analyze_chunk(client: AsyncGroq, chunk_text: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
    prompt = build_analysis_prompt(chunk_text, chunk_index, total_chunks)
    try:
        result_json = await call_groq_with_backoff(client, GROQ_MODEL_PRIMARY, prompt)
    except RateLimitError:
        logger.warning(f"Rate limit on primary model, switching to fallback for chunk {chunk_index}")
        result_json = await call_groq_with_backoff(client, GROQ_MODEL_FALLBACK, prompt)
    except Exception as e:
        logger.error(f"Chunk {chunk_index} failed: {e}")
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
    merged_clauses = {}
    merged_missing = {}
    overall_risk_levels = {"Low": 0, "Medium": 1, "High": 2}
    max_risk_score = 0
    summaries = []

    for res in results:
        for clause in res.get("clause_analysis", []):
            key = clause.get("clause_number") or clause.get("title")
            if not key:
                key = f"unknown_{id(clause)}"
            existing = merged_clauses.get(key)
            if not existing or (clause.get("redline") and not existing.get("redline")):
                merged_clauses[key] = clause
            elif len(clause.get("reason", "")) > len(existing.get("reason", "")):
                merged_clauses[key] = clause

        for missing in res.get("missing_clauses", []):
            title = missing.get("title")
            if title and title not in merged_missing:
                merged_missing[title] = missing

        risk = res.get("overall_risk", "Low")
        risk_score = overall_risk_levels.get(risk, 0)
        if risk_score > max_risk_score:
            max_risk_score = risk_score

        if res.get("executive_summary"):
            summaries.append(res["executive_summary"])

    final_risk = {0: "Low", 1: "Medium", 2: "High"}[max_risk_score]
    final_summary = " ".join(summaries) if summaries else "No executive summary available."

    return {
        "clause_analysis": list(merged_clauses.values()),
        "missing_clauses": list(merged_missing.values()),
        "overall_risk": final_risk,
        "executive_summary": final_summary
    }

# -------------------------------
# Health check
# -------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "docs_loaded": True}

# -------------------------------
# /analyze endpoint (multi‑step with robust PDF parsing)
# -------------------------------
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    # 1. Parse PDF with multiple fallbacks
    file_bytes = await file.read()
    contract_text = ""
    filename = file.filename

    # Try LlamaParse first (requires API key)
    if os.getenv("LLAMA_CLOUD_API_KEY"):
        try:
            parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="text")
            documents = await asyncio.to_thread(
                parser.load_data,
                file_bytes,
                extra_info={"file_name": filename}
            )
            contract_text = "\n".join([doc.text for doc in documents])
            print(f"LlamaParse extracted {len(contract_text)} chars")
        except Exception as e:
            print(f"LlamaParse failed: {e}")

    # Fallback to pdfplumber
    if not contract_text.strip():
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        contract_text += text + "\n"
            print(f"pdfplumber extracted {len(contract_text)} chars")
        except Exception as e:
            print(f"pdfplumber failed: {e}")

    # Final fallback: PyPDF2
    if not contract_text.strip():
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    contract_text += text + "\n"
            print(f"PyPDF2 extracted {len(contract_text)} chars")
        except Exception as e:
            print(f"PyPDF2 failed: {e}")

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF. Ensure the PDF contains selectable text (not scanned).")

    # 2. Split into overlapping chunks
    chunks = split_text_with_overlap(contract_text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    logger.info(f"Split contract into {len(chunks)} chunks")

    # 3. Initialize Groq client
    groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    # 4. Analyze chunks concurrently (with semaphore to avoid rate limits)
    semaphore = asyncio.Semaphore(3)
    async def analyze_with_semaphore(chunk, idx):
        async with semaphore:
            return await analyze_chunk(groq_client, chunk, idx, len(chunks))

    tasks = [analyze_with_semaphore(chunk, i) for i, chunk in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks)

    # 5. Merge and return
    final_report = merge_results(chunk_results)
    return final_report

# -------------------------------
# (Optional) weekly digest endpoint – requires vector index built by index_builder.py
# -------------------------------
from llama_index.core import StorageContext, load_index_from_storage

storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = None
try:
    index = load_index_from_storage(storage_context)
    logger.info("Loaded vector index for weekly digest")
except:
    logger.warning("No vector index found – weekly digest disabled")

@app.get("/weekly-digest")
async def weekly_digest():
    if not index:
        raise HTTPException(status_code=501, detail="Weekly digest not available (no index found)")
    retriever = index.as_retriever(similarity_top_k=5)
    # Example query; you can modify as needed
    nodes = retriever.retrieve("common legal risks in recent contracts")
    return {"digest": [{"text": node.text, "score": node.score} for node in nodes]}