import os
import asyncio
import json
import logging
import io
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from llama_parse import LlamaParse
from openai import AsyncOpenAI
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pdfplumber
import PyPDF2

# -------------------------------
# Configuration
# -------------------------------
MAX_TOKENS_PER_CHUNK = 25000   # Together AI has 32k context, so we can use large chunks
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
# Compact prompt
# -------------------------------
def build_analysis_prompt(chunk_text: str, chunk_index: int, total_chunks: int) -> str:
    return f"""Analyze contract chunk {chunk_index+1}/{total_chunks} for Indian law. Return ONLY JSON:
{{
  "clause_analysis": [{{"clause_number":"","title":"","risk_level":"Low/Medium/High","legal_basis":"Indian law section","reason":"2 sentences","redline":"exact change or 'No change'"}}],
  "missing_clauses": [{{"title":"","risk_level":"High","legal_basis":"","reason":"","proposed_clause_text":""}}],
  "overall_risk":"Low/Medium/High",
  "executive_summary":"1 paragraph"
}}
Essential clauses: limitation of liability, indemnity, termination, DPDP Act, non‑compete, non‑solicit, arbitration (India seat), governing law India, force majeure, entire agreement, amendment, severability, waiver, assignment.

Chunk: {chunk_text}"""

# -------------------------------
# Together AI call with retry
# -------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_together(client: AsyncOpenAI, prompt: str) -> str:
    response = await client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def analyze_chunk(client: AsyncOpenAI, chunk_text: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
    prompt = build_analysis_prompt(chunk_text, chunk_index, total_chunks)
    try:
        result_json = await call_together(client, prompt)
        return json.loads(result_json)
    except Exception as e:
        logger.error(f"Chunk {chunk_index} failed: {e}")
        return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "High", "executive_summary": f"Analysis failed for chunk {chunk_index}"}

# -------------------------------
# Merge results
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
# /analyze endpoint
# -------------------------------
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    # Parse PDF
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
        except Exception as e:
            print(f"LlamaParse failed: {e}")

    if not contract_text.strip():
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        contract_text += text + "\n"
        except Exception as e:
            print(f"pdfplumber failed: {e}")

    if not contract_text.strip():
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    contract_text += text + "\n"
        except Exception as e:
            print(f"PyPDF2 failed: {e}")

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    chunks = split_text_with_overlap(contract_text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    logger.info(f"Split into {len(chunks)} chunks")

    together_client = AsyncOpenAI(
        api_key=os.getenv("TOGETHER_API_KEY"),
        base_url="https://api.together.xyz/v1"
    )

    semaphore = asyncio.Semaphore(3)
    async def analyze_with_semaphore(chunk, idx):
        async with semaphore:
            return await analyze_chunk(together_client, chunk, idx, len(chunks))

    tasks = [analyze_with_semaphore(chunk, i) for i, chunk in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks)
    final_report = merge_results(chunk_results)
    return final_report

# -------------------------------
# Weekly digest (optional, disabled for now)
# -------------------------------
@app.get("/weekly-digest")
async def weekly_digest():
    raise HTTPException(status_code=501, detail="Weekly digest not available")