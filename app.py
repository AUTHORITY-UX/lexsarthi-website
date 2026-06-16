import os
import json
import io
from typing import List, Optional, Literal
from enum import Enum

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import PyPDF2
from openai import OpenAI

# ------------------- Pydantic Schemas -------------------
class AgreementType(str, Enum):
    REGISTRATION = "Domain Registration Agreement"
    TRANSFER = "Domain Transfer Agreement"
    RENEWAL = "Domain Renewal Agreement"
    RESELLER = "Domain Reseller Agreement"
    PARKING = "Domain Parking Agreement"
    SUNRISE = "Sunrise Registration Agreement"
    LRO = "Legal Rights Objection Agreement"
    OTHER = "Other"

class CriticalClause(BaseModel):
    clause_reference: str
    title: str
    risk: Literal["Low", "Medium", "High", "Critical"]
    explanation: str
    suggested_amendment: Optional[str] = None

class DomainAgreementAnalysis(BaseModel):
    agreement_type: AgreementType
    confidence: float = Field(ge=0.0, le=1.0)
    registrar: Optional[str] = None
    registrant: Optional[str] = None
    domain_name: Optional[str] = None
    term_years: Optional[int] = None
    governing_law: Optional[str] = None
    key_obligations: List[str] = []
    critical_clauses: List[CriticalClause] = []
    overall_risk: Literal["Low", "Medium", "High"] = "Low"
    summary: str
    recommended_action: str
    disclaimer: str = "This analysis is AI-generated and does not constitute legal advice. Always consult a qualified attorney."

# ------------------- FastAPI App -------------------
app = FastAPI(title="LexSarthi API", version="1.0")

# CORS – allow your frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dbeba57b.lexsarthi-website.pages.dev",
        "https://advocacyalawfrim.in",
        "https://www.advocacyalawfrim.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- OpenRouter Client (via OpenAI SDK) -------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # or use OPENAI_API_KEY if you set that
)

# Choose a fast model – change if you prefer
MODEL = "meta-llama/llama-3.1-8b-instruct"  # cheap & fast, good for classification

# ------------------- Agent Function -------------------
async def analyze_domain_agreement(text: str) -> dict:
    taxonomy = """
    The recognized types of domain name agreements are:
    1. Domain Registration Agreement: contract between registrant and registrar for initial registration.
    2. Domain Transfer Agreement: agreement to transfer ownership from one party to another.
    3. Domain Renewal Agreement: extends the registration period.
    4. Domain Reseller Agreement: allows a reseller to offer domain registrations.
    5. Domain Parking Agreement: for monetizing unused domains.
    6. Sunrise Registration Agreement: for trademark holders during new TLD launches.
    7. Legal Rights Objection Agreement: dispute resolution over domain names.
    """

    system_prompt = f"""
    You are LexSarthi's Domain Agreement Classifier. 
    Your task is to analyze the provided agreement text and classify it according to the taxonomy below.
    Output **only** a JSON object that exactly matches the Pydantic schema provided in the user's request.

    Taxonomy:
    {taxonomy}

    STRICT RULES:
    - Only output valid JSON.
    - Do not include markdown, comments, or extra text.
    - Use the exact field names and types as in the schema.
    - If unsure about a field, use null (or a sensible default).
    """

    user_prompt = f"""
    Analyze the following domain agreement text and return JSON matching this schema:
    {DomainAgreementAnalysis.schema_json(indent=2)}

    Agreement Text:
    {text[:12000]}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},  # works with OpenRouter too
            max_tokens=4096
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        validated = DomainAgreementAnalysis(**data)
        return validated.dict()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Schema validation error: {str(e)}")

# ------------------- Endpoints -------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/analyze-domain-agreement", response_model=DomainAgreementAnalysis)
async def classify_domain_agreement(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    if not file and not text:
        raise HTTPException(400, "Either upload a file or provide raw text.")
    
    content = ""
    if file:
        contents = await file.read()
        if file.filename.lower().endswith(".pdf"):
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
                content = " ".join(page.extract_text() for page in pdf_reader.pages)
            except Exception as e:
                raise HTTPException(400, f"PDF parsing failed: {str(e)}")
        else:
            content = contents.decode("utf-8", errors="ignore")
    else:
        content = text
    
    if len(content.strip()) < 50:
        raise HTTPException(400, "Text is too short to analyze meaningfully.")
    
    return await analyze_domain_agreement(content)