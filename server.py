import os
import asyncio
import json
import logging
import io
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from llama_parse import LlamaParse
from groq import AsyncGroq, RateLimitError
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pdfplumber
import PyPDF2

# LlamaIndex for vector search (weekly digest)
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, SimpleDirectoryReader
from llama_index.core.schema import Document
from llama_index.core.retrievers import VectorIndexRetriever

# -------------------------------
# Configuration
# -------------------------------
GROQ_MODEL_PRIMARY = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"
MAX_TOKENS_PER_CHUNK = 6000
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

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
# Contract Analysis Helpers (same as before)
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
        logger.warning(f"Rate limit on primary, fallback for chunk {chunk_index}")
        result_json = await call_groq_with_backoff(client, GROQ_MODEL_FALLBACK, prompt)
    except Exception as e:
        logger.error(f"Chunk {chunk_index} failed: {e}")
        return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "High", "executive_summary": f"Analysis failed for chunk {chunk_index}"}
    try:
        return json.loads(result_json)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from chunk {chunk_index}: {result_json[:200]}")
        return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "High", "executive_summary": f"JSON parse error in chunk {chunk_index}"}

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
    file_bytes = await file.read()
    contract_text = ""
    filename = file.filename

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

    chunks = split_text_with_overlap(contract_text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    logger.info(f"Split contract into {len(chunks)} chunks")

    groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    semaphore = asyncio.Semaphore(3)
    async def analyze_with_semaphore(chunk, idx):
        async with semaphore:
            return await analyze_chunk(groq_client, chunk, idx, len(chunks))

    tasks = [analyze_with_semaphore(chunk, i) for i, chunk in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks)
    final_report = merge_results(chunk_results)
    return final_report

# -------------------------------
# Weekly Digest – Legal Index (National + International)
# -------------------------------
LEGAL_INDEX_PATH = "./legal_index"
index = None
retriever = None

def load_legal_index():
    global index, retriever
    if not os.path.exists(LEGAL_INDEX_PATH):
        logger.warning("Legal index not found. Run index_builder.py first.")
        return
    try:
        storage_context = StorageContext.from_defaults(persist_dir=LEGAL_INDEX_PATH)
        index = load_index_from_storage(storage_context)
        retriever = VectorIndexRetriever(index, similarity_top_k=5)
        logger.info("Legal index loaded for weekly digest")
    except Exception as e:
        logger.error(f"Failed to load legal index: {e}")

# Try to load index on startup
load_legal_index()

@app.get("/weekly-digest")
async def weekly_digest(q: Optional[str] = Query(None, description="Query for legal updates (e.g., 'data protection amendments', 'CISG updates')")):
    if not index or not retriever:
        raise HTTPException(status_code=501, detail="Legal index not built. Run index_builder.py first.")
    
    if not q:
        q = "recent developments in Indian and international laws relevant to contracts"

    # Retrieve relevant legal documents (text chunks)
    nodes = retriever.retrieve(q)
    if not nodes:
        return {"digest": [], "message": "No relevant legal provisions found for your query."}

    # Format the retrieved legal texts
    digest = []
    for node in nodes:
        digest.append({
            "text": node.text[:1000],  # limit length
            "score": node.score,
            "metadata": node.metadata
        })
    
    # Optional: Use LLM to summarise the retrieved laws into a weekly update
    # (For simplicity, return raw chunks; you can add a summarisation step later)
    return {"query": q, "digest": digest}