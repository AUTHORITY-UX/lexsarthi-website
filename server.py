import os
import json
import asyncio
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from openai import AsyncOpenAI
import pdfplumber
import PyPDF2
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# -------------------------------
# Database setup (for future user accounts & history)
# -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lexsarthi.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContractAnalysis(Base):
    __tablename__ = "contract_analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    analysis_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------------------
# Security (for optional authenticated endpoints)
# -------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)  # auto_error=False to make optional

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(lambda: SessionLocal())):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except JWTError:
        return None

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
# OpenRouter client (free tier, large context)
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

PRIMARY_MODEL = "google/gemini-1.5-pro"      # 2M context, free tier
FALLBACK_MODEL = "openai/gpt-3.5-turbo"     # 16k context

MAX_TOKENS_PER_CHUNK = 120000   # only used for extremely long documents
OVERLAP_TOKENS = 500
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# -------------------------------
# Helper: split text with overlap (safety net)
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
# Strict, clause‑focused prompt (40‑year corporate lawyer persona)
# -------------------------------
def build_analysis_prompt(chunk_text: str, chunk_index: int, total_chunks: int) -> str:
    return f"""You are a corporate lawyer with 40 years of experience in Indian and international contract law, having advised top law firms and multinational corporations. Analyze the following part of a contract (chunk {chunk_index+1} of {total_chunks}).

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
   - `risk_level`: "High"
   - `legal_basis`: relevant Indian law
   - `reason`: why it is required
   - `proposed_clause_text`: draft wording as it should appear in the contract.

Essential clauses to check: limitation of liability, indemnity, termination for convenience, data protection (DPDP Act compliance), non-compete, non-solicit, arbitration (with Indian seat), governing law (India), force majeure, notice, entire agreement, amendment, severability, waiver, assignment.

4. **Overall risk** for this chunk: "Low", "Medium", or "High" based on the worst clause in this chunk.

5. **Executive summary** (one paragraph) highlighting the most critical risks in this chunk, written in the style of a senior partner.

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
# LLM call with retry and fallback
# -------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_llm(model: str, prompt: str) -> str:
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
    result = response.choices[0].message.content
    # Clean markdown fences
    cleaned = result.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

async def analyze_chunk(chunk_text: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
    prompt = build_analysis_prompt(chunk_text, chunk_index, total_chunks)
    try:
        result_json = await call_llm(PRIMARY_MODEL, prompt)
        return json.loads(result_json)
    except Exception as e:
        print(f"Primary model failed for chunk {chunk_index}: {e}. Falling back to {FALLBACK_MODEL}")
        try:
            result_json = await call_llm(FALLBACK_MODEL, prompt)
            return json.loads(result_json)
        except Exception as e2:
            print(f"Fallback also failed for chunk {chunk_index}: {e2}")
            return {
                "clause_analysis": [],
                "missing_clauses": [],
                "overall_risk": "High",
                "executive_summary": f"Analysis failed for chunk {chunk_index}: {str(e2)}"
            }

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
# PDF text extraction (robust)
# -------------------------------
async def extract_text(file_bytes: bytes, filename: str) -> str:
    # pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    # PyPDF2
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")
    # LlamaParse fallback
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
# Public /analyze endpoint (no authentication required)
# -------------------------------
@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional)  # optional, not enforced
):
    file_bytes = await file.read()
    contract_text = await extract_text(file_bytes, file.filename)
    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    chunks = split_text_with_overlap(contract_text, MAX_TOKENS_PER_CHUNK, OVERLAP_TOKENS)
    print(f"Split contract into {len(chunks)} chunks")

    semaphore = asyncio.Semaphore(3)
    async def analyze_with_semaphore(chunk, idx):
        async with semaphore:
            return await analyze_chunk(chunk, idx, len(chunks))

    tasks = [analyze_with_semaphore(chunk, i) for i, chunk in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks)
    final_report = merge_results(chunk_results)

    # If user is logged in, save analysis to history (optional)
    if current_user:
        db = SessionLocal()
        analysis = ContractAnalysis(
            user_id=current_user.id,
            filename=file.filename,
            analysis_json=json.dumps(final_report)
        )
        db.add(analysis)
        db.commit()
        db.close()

    return final_report

# -------------------------------
# Authentication endpoints (for future use)
# -------------------------------
@app.post("/register")
async def register(email: str, password: str, db: Session = Depends(lambda: SessionLocal())):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(password)
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created successfully"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(lambda: SessionLocal())):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/history")
async def get_history(current_user: User = Depends(get_current_user_optional), db: Session = Depends(lambda: SessionLocal())):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    analyses = db.query(ContractAnalysis).filter(ContractAnalysis.user_id == current_user.id).order_by(ContractAnalysis.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "created_at": a.created_at.isoformat(),
            "summary": json.loads(a.analysis_json).get("executive_summary", "")[:200]
        }
        for a in analyses
    ]

@app.get("/history/{analysis_id}")
async def get_analysis(analysis_id: int, current_user: User = Depends(get_current_user_optional), db: Session = Depends(lambda: SessionLocal())):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    analysis = db.query(ContractAnalysis).filter(ContractAnalysis.id == analysis_id, ContractAnalysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return json.loads(analysis.analysis_json)

@app.delete("/history/{analysis_id}")
async def delete_analysis(analysis_id: int, current_user: User = Depends(get_current_user_optional), db: Session = Depends(lambda: SessionLocal())):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    analysis = db.query(ContractAnalysis).filter(ContractAnalysis.id == analysis_id, ContractAnalysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.delete(analysis)
    db.commit()
    return {"message": "Deleted"}

@app.get("/health")
async def health():
    return {"status": "ok"}