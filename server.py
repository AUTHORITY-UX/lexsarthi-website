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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
MODEL = "openai/gpt-3.5-turbo"  # free tier on OpenRouter, reliable

def build_prompt(text: str) -> str:
    return f"""You are a 40-year corporate lawyer. Analyze this contract and return ONLY JSON:
{{
  "clause_analysis": [
    {{"clause_number": "", "title": "", "risk_level": "Low/Medium/High", "legal_basis": "Indian law", "reason": "...", "redline": "..."}}
  ],
  "missing_clauses": [
    {{"title": "", "risk_level": "High", "legal_basis": "", "reason": "", "proposed_clause_text": ""}}
  ],
  "overall_risk": "Low/Medium/High",
  "executive_summary": "..."
}}
Contract: {text[:20000]}"""

async def extract_text(file_bytes: bytes, filename: str) -> str:
    # Try pdfplumber (fast, no key needed)
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
        return text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")
    return ""

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    file_bytes = await file.read()
    contract_text = await extract_text(file_bytes, file.filename)
    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted.")
    prompt = build_prompt(contract_text)
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_headers={"HTTP-Referer": "https://advocacyalawfrim.in", "X-Title": "LexSarthi"}
        )
        result = response.choices[0].message.content
        # Clean markdown
        if result.startswith("```json"):
            result = result[7:-3]
        elif result.startswith("```"):
            result = result[3:-3]
        return json.loads(result)
    except Exception as e:
        # Return the error as a JSON that frontend can display
        return {
            "clause_analysis": [],
            "missing_clauses": [],
            "overall_risk": "Error",
            "executive_summary": f"LLM call failed: {str(e)}. Check OpenRouter API key and model availability."
        }