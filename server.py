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
# OpenRouter client (Gemini 1.5 Pro)
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
PRIMARY_MODEL = "google/gemini-1.5-pro"   # 2M context, free tier

# -------------------------------
# 40‑year corporate lawyer prompt
# -------------------------------
def build_full_analysis_prompt(contract_text: str) -> str:
    return f"""You are a corporate lawyer with 40 years of experience in Indian and international contract law, having advised top law firms and multinational corporations. Analyze the full contract below with the depth and precision expected from a senior partner.

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
  "executive_summary": "one paragraph highlighting most critical risks, written in the style of a senior lawyer's memo"
}}

Essential clauses to check (include if missing in missing_clauses):
- Limitation of liability (caps, exceptions)
- Indemnity (scope, caps, survival)
- Termination for convenience and cause
- Data protection (DPDP Act, 2025 compliance)
- Non-compete, non-solicit, non-disclosure
- Arbitration (Indian seat, e.g., New Delhi; institutional rules like MCIA or LCIA India)
- Governing law (India)
- Force majeure (with COVID/epidemic clause)
- Notice, entire agreement, amendment, severability, waiver, assignment

Contract text:
{contract_text}
"""

# -------------------------------
# PDF text extraction (fallback chain)
# -------------------------------
async def extract_text_from_pdf(file_bytes: bytes, filename: str) -> str:
    contract_text = ""

    # Try LlamaParse if API key exists
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

    # Fallback to pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    contract_text += text + "\n"
        if contract_text.strip():
            return contract_text
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # Final fallback: PyPDF2
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                contract_text += text + "\n"
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
    # 1. Read file and extract text
    file_bytes = await file.read()
    contract_text = await extract_text_from_pdf(file_bytes, file.filename)

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF. Ensure the PDF contains selectable text (not scanned).")

    # 2. Build prompt
    prompt = build_full_analysis_prompt(contract_text)

    # 3. Call OpenRouter (Gemini 1.5 Pro)
    try:
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

        # Clean markdown if any
        if result_json.startswith("```json"):
            result_json = result_json[7:-3]
        elif result_json.startswith("```"):
            result_json = result_json[3:-3]

        return json.loads(result_json)

    except Exception as e:
        print(f"OpenRouter call failed: {e}")
        # Optional fallback to Claude
        try:
            fallback_response = await openrouter_client.chat.completions.create(
                model="anthropic/claude-3.5-sonnet",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            result_json = fallback_response.choices[0].message.content
            if result_json.startswith("```json"):
                result_json = result_json[7:-3]
            elif result_json.startswith("```"):
                result_json = result_json[3:-3]
            return json.loads(result_json)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e2)}")