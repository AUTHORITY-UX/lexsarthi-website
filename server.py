import os
import json
import asyncio
import io
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import pdfplumber
import PyPDF2

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

# Use the reliable free router (picks best available free model)
MODEL = "openrouter/free"

# -------------------------------
# 40‑year corporate lawyer prompt
# -------------------------------
def build_prompt(contract_text: str) -> str:
    return f"""You are a corporate lawyer with 40 years of experience in Indian and international contract law. Analyze the full contract below.

Return ONLY valid JSON with this exact structure (no markdown, no extra text):
{{
  "clause_analysis": [
    {{
      "clause_number": "string",
      "title": "short clause name",
      "risk_level": "Low/Medium/High",
      "legal_basis": "Indian law section",
      "reason": "detailed explanation (2-3 sentences)",
      "redline": "exact suggested wording change or 'No change'"
    }}
  ],
  "missing_clauses": [
    {{
      "title": "clause name",
      "risk_level": "High",
      "legal_basis": "relevant law",
      "reason": "why required",
      "proposed_clause_text": "draft wording"
    }}
  ],
  "overall_risk": "Low/Medium/High",
  "executive_summary": "one paragraph"
}}

Essential clauses to check (add to missing_clauses if absent):
- Limitation of liability
- Indemnity
- Termination
- Data protection (DPDP Act 2025)
- Non-compete, non-solicit
- Arbitration (Indian seat)
- Governing law (India)
- Force majeure
- Notice, entire agreement, amendment, severability, waiver, assignment

Contract:
{contract_text}
"""

# -------------------------------
# PDF text extraction
# -------------------------------
async def extract_text(file_bytes: bytes, filename: str) -> str:
    # Try LlamaParse if key exists
    if os.getenv("LLAMA_CLOUD_API_KEY"):
        try:
            from llama_parse import LlamaParse
            parser = LlamaParse(api_key=os.getenv("LLAMA_CLOUD_API_KEY"), result_type="text")
            docs = await asyncio.to_thread(parser.load_data, file_bytes, extra_info={"file_name": filename})
            text = "\n".join(d.text for d in docs)
            if text.strip():
                return text
        except Exception as e:
            print(f"LlamaParse failed: {e}")

    # pdfplumber fallback
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # PyPDF2 fallback
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    return ""

# -------------------------------
# Health check
# -------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# -------------------------------
# /analyze endpoint
# -------------------------------
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    file_bytes = await file.read()
    contract_text = await extract_text(file_bytes, file.filename)

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    prompt = build_prompt(contract_text)

    # Try primary model (openrouter/free)
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": "https://advocacyalawfrim.in",
                "X-Title": "LexSarthi",
            }
        )
        result_text = response.choices[0].message.content

        # Clean markdown
        cleaned = result_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        return json.loads(cleaned)

    except Exception as e:
        print(f"OpenRouter error with {MODEL}: {e}")
        # Fallback: try a specific free model
        try:
            fallback_model = "google/gemini-2.0-flash-lite-preview-02-05:free"
            response = await client.chat.completions.create(
                model=fallback_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            result_text = response.choices[0].message.content
            cleaned = result_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned)
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return {
                "clause_analysis": [],
                "missing_clauses": [],
                "overall_risk": "Unknown",
                "executive_summary": f"Analysis failed: {str(e)}. Please try again later."
            }