import os
import json
import asyncio
import io
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import pdfplumber
import PyPDF2

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
# OpenRouter client (free, large context)
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Use a free model with 1M context (no truncation)
MODEL = "google/gemini-2.0-flash-exp:free"

# -------------------------------
# 40‑year corporate lawyer prompt (JSON first)
# -------------------------------
def build_json_prompt(contract_text: str) -> str:
    return f"""You are a corporate lawyer with 40 years of experience in Indian and international contract law. Analyze the full contract below.

Return ONLY valid JSON with this exact structure (no markdown, no extra text):
{{
  "clause_analysis": [
    {{
      "clause_number": "string (e.g., '4.2', 'Indemnity')",
      "title": "short clause name",
      "risk_level": "Low/Medium/High",
      "legal_basis": "specific Indian law section (e.g., 'Section 124 of Indian Contract Act, 1872')",
      "reason": "detailed explanation (2-3 sentences)",
      "redline": "exact suggested wording change or 'No change'"
    }}
  ],
  "missing_clauses": [
    {{
      "title": "clause name (e.g., 'Data Protection under DPDP Act')",
      "risk_level": "High",
      "legal_basis": "relevant Indian law section",
      "reason": "why it is required",
      "proposed_clause_text": "draft wording"
    }}
  ],
  "overall_risk": "Low/Medium/High",
  "executive_summary": "one paragraph highlighting most critical risks"
}}

Essential clauses to check (add to missing_clauses if absent):
- Limitation of liability (caps, exceptions)
- Indemnity (scope, caps, survival)
- Termination for convenience and cause
- Data protection (DPDP Act, 2025 compliance)
- Non-compete, non-solicit, non-disclosure
- Arbitration (Indian seat, e.g., New Delhi)
- Governing law (India)
- Force majeure (including epidemics)
- Notice, entire agreement, amendment, severability, waiver, assignment

Contract:
{contract_text}
"""

def build_summary_prompt(contract_text: str) -> str:
    return f"""You are a 40‑year corporate lawyer. The contract below could not be analysed in strict JSON. Please provide a concise legal risk summary in the following format:

OVERALL RISK: [Low/Medium/High]
EXECUTIVE SUMMARY: (one paragraph)
KEY CLAUSES WITH RISKS:
- Clause name/number: risk level, reason, suggested change (if any)
MISSING ESSENTIAL CLAUSES: (list clauses like indemnity, DPDP, force majeure, etc.)

Contract (excerpt, first 15000 chars):
{contract_text[:15000]}
"""

# -------------------------------
# PDF text extraction (fallback chain)
# -------------------------------
async def extract_text_from_pdf(file_bytes: bytes, filename: str) -> str:
    contract_text = ""

    # 1. LlamaParse if key present
    if os.getenv("LLAMA_CLOUD_API_KEY"):
        try:
            from llama_parse import LlamaParse
            parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="text")
            documents = await asyncio.to_thread(
                parser.load_data,
                file_bytes,
                extra_info={"file_name": filename}
            )
            contract_text = "\n".join([doc.text for doc in documents])
            if contract_text.strip():
                return contract_text
        except Exception as e:
            print(f"LlamaParse failed: {e}")

    # 2. pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text_parts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            contract_text = "\n".join(text_parts)
        if contract_text.strip():
            return contract_text
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # 3. PyPDF2
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        contract_text = "\n".join(text_parts)
        return contract_text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    return ""

# -------------------------------
# Health check
# -------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "docs_loaded": True}

# -------------------------------
# Main /analyze endpoint
# -------------------------------
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    # 1. Read and extract text
    file_bytes = await file.read()
    contract_text = await extract_text_from_pdf(file_bytes, file.filename)

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF. Ensure the PDF contains selectable text (not scanned).")

    # 2. Try JSON analysis first
    json_prompt = build_json_prompt(contract_text)
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": json_prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": "https://advocacyalawfrim.in",
                "X-Title": "LexSarthi",
            }
        )
        result_text = response.choices[0].message.content

        # Clean markdown fences
        cleaned = result_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

        # Validate required keys
        if "clause_analysis" in data and "missing_clauses" in data and "overall_risk" in data:
            return data
        else:
            raise ValueError("JSON missing required keys")

    except (json.JSONDecodeError, ValueError, Exception) as e:
        print(f"JSON analysis failed, falling back to summary: {e}")

        # 3. Fallback to plain‑text summary
        summary_prompt = build_summary_prompt(contract_text)
        summary_response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2,
        )
        summary_text = summary_response.choices[0].message.content

        # Return a structure the frontend can still display
        return {
            "clause_analysis": [],
            "missing_clauses": [],
            "overall_risk": "Review Required",
            "executive_summary": summary_text,
            "note": "Structured JSON could not be generated; a textual risk summary is provided above."
        }