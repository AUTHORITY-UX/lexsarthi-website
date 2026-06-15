import os
import asyncio
import json
import logging
import io
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from llama_parse import LlamaParse
import google.generativeai as genai
import litellm
from litellm import acompletion
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pdfplumber
import PyPDF2

# -------------------------------
# Configuration
# -------------------------------
MAX_TOKENS_PER_CHUNK = 30000   # Gemini has 2M context, but we keep chunking for safety
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

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-pro")  # 2M context, free tier

# Configure LiteLLM for fallbacks (OpenRouter, Groq)
litellm.set_verbose = False

# -------------------------------
# Helper: split text with overlap (still useful for very long contracts)
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
# Strict legal prompt (same as before)
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
# Primary: Gemini call (with retry)
# -------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def call_gemini(prompt: str) -> str:
    response = await gemini_model.generate_content_async(prompt)
    return response.text

# -------------------------------
# Fallback: LiteLLM (OpenRouter / Groq)
# -------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def call_litellm(model: str, prompt: str) -> str:
    response = await acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

# -------------------------------
# Multi‑provider orchestration
# -------------------------------
async def analyze_chunk(chunk_text: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
    prompt = build_analysis_prompt(chunk_text, chunk_index, total_chunks)
    
    # Try Gemini first
    try:
        result_json = await call_gemini(prompt)
        # Gemini sometimes returns markdown; clean it
        if result_json.startswith("```json"):
            result_json = result_json[7:-3]
        elif result_json.startswith("```"):
            result_json = result_json[3:-3]
        return json.loads(result_json)
    except Exception as e:
        logger.warning(f"Gemini failed for chunk {chunk_index}: {e}, falling back to OpenRouter")
        
        # Fallback 1: OpenRouter (free models)
        try:
            openrouter_models = [
                "openrouter/deepseek/deepseek-chat",
                "openrouter/google/gemini-2.0-flash-exp:free",
                "openrouter/meta-llama/llama-3.2-3b-instruct:free"
            ]
            for model in openrouter_models:
                try:
                    result_json = await call_litellm(model, prompt)
                    # Clean markdown if present
                    if result_json.startswith("```json"):
                        result_json = result_json[7:-3]
                    elif result_json.startswith("```"):
                        result_json = result_json[3:-3]
                    return json.loads(result_json)
                except Exception as inner_e:
                    logger.warning(f"OpenRouter model {model} failed: {inner_e}")
                    continue
            raise Exception("All OpenRouter fallbacks failed")
        except Exception as e:
            logger.error(f"All fallbacks failed for chunk {chunk_index}: {e}")
            return {"clause_analysis": [], "missing_clauses": [], "overall_risk": "High", "executive_summary": f"Analysis failed for chunk {chunk_index}"}

# -------------------------------
# Merge results (same as before)
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
# Add to imports
from openai import AsyncOpenAI

# Initialize OpenRouter client (OpenAI-compatible)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Choose a model with large context – Gemini 1.5 Pro (2M) or Claude 3.5 Sonnet (200k)
PRIMARY_MODEL = "google/gemini-1.5-pro"  # 2M context – no chunking needed for 99% of contracts

async def analyze_contract_full(file: UploadFile = File(...)):
    # 1. Parse PDF (same as before – LlamaParse etc.)
    # ...
    # 2. Instead of chunking, send the whole text (or split into < 1M tokens)
    # Gemini 1.5 Pro can handle the entire contract at once.
    
    prompt = build_full_analysis_prompt(contract_text)  # single prompt, no chunk index
    response = await openrouter_client.chat.completions.create(
        model=PRIMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
        extra_headers={
            "HTTP-Referer": "https://advocacyalawfrim.in",
            "X-Title": "LexSarthi",
        }
    )
    result_json = response.choices[0].message.content
    # Clean and parse JSON
    return json.loads(result_json)               
# -------------------------------
# Weekly digest (placeholder – can be implemented later)
# -------------------------------
@app.get("/weekly-digest")
async def weekly_digest():
    raise HTTPException(status_code=501, detail="Weekly digest not yet implemented")