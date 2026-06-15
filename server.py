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

# Model names (working on OpenRouter free tier)
MODEL_SMALL = "openai/gpt-3.5-turbo"           # 16k context, fast, free
MODEL_LARGE = "google/gemini-2.0-flash-exp:free"  # 1M context, free, works with long documents

# Threshold: switch to large model if estimated tokens > 120k (approx 480k chars)
TOKEN_THRESHOLD = 120000

# -------------------------------
# 40‑year corporate lawyer prompt (full text, no truncation)
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
# PDF text extraction (full document)
# -------------------------------
async def extract_text(file_bytes: bytes, filename: str) -> str:
    # Try pdfplumber first (fast, handles large PDFs)
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # Fallback to PyPDF2
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    # Optional: LlamaParse if key exists (for scanned PDFs)
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
    # 1. Extract full text
    file_bytes = await file.read()
    contract_text = await extract_text(file_bytes, file.filename)

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF. Ensure the PDF contains selectable text (not scanned).")

    # 2. Estimate token count (rough: 4 chars per token)
    token_estimate = len(contract_text) // 4

    # 3. Choose model based on size
    if token_estimate > TOKEN_THRESHOLD:
        model = MODEL_LARGE
        print(f"Using large model {model} (estimated {token_estimate} tokens)")
    else:
        model = MODEL_SMALL
        print(f"Using small model {model} (estimated {token_estimate} tokens)")

    # 4. Build prompt (full text, no truncation)
    prompt = build_prompt(contract_text)

    # 5. Call OpenRouter
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": "https://advocacyalawfrim.in",
                "X-Title": "LexSarthi",
            }
        )
        result_text = response.choices[0].message.content

        # Clean markdown if any
        cleaned = result_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return data

    except Exception as e:
        print(f"OpenRouter error with model {model}: {e}")
        # Fallback: try the other model if the first fails (e.g., rate limit)
        fallback_model = MODEL_LARGE if model == MODEL_SMALL else MODEL_SMALL
        try:
            print(f"Falling back to {fallback_model}")
            response = await client.chat.completions.create(
                model=fallback_model,
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
            return json.loads(cleaned)
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return {
                "clause_analysis": [],
                "missing_clauses": [],
                "overall_risk": "Error",
                "executive_summary": f"Analysis failed: {str(e)}. Please try again later."
            }