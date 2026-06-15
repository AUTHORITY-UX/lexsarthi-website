import os
import json
import asyncio
import io
from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from openai import AsyncOpenAI
import pdfplumber
import PyPDF2
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# -------------------------------
# Database setup
# -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lexsarthi.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
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
    analysis_json = Column(Text)  # store JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------------------
# Security
# -------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(lambda: SessionLocal())):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

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
# OpenRouter client
# -------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL = "google/gemini-2.0-flash-exp:free"   # 1M context, free

# -------------------------------
# Prompt (unchanged)
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
    # Try pdfplumber first
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
        if text.strip():
            return text
    except Exception as e:
        print(f"PyPDF2 failed: {e}")

    # LlamaParse if key exists (for scanned PDFs)
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
# Authentication endpoints
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

# -------------------------------
# Contract analysis endpoint (protected, saves history)
# -------------------------------
@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(lambda: SessionLocal())
):
    file_bytes = await file.read()
    contract_text = await extract_text(file_bytes, file.filename)

    if not contract_text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    prompt = build_prompt(contract_text)
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_headers={"HTTP-Referer": "https://advocacyalawfrim.in", "X-Title": "LexSarthi"}
        )
        result_text = response.choices[0].message.content
        cleaned = result_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        data = json.loads(cleaned)

        # Save to history
        analysis = ContractAnalysis(
            user_id=current_user.id,
            filename=file.filename,
            analysis_json=json.dumps(data)
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return data
    except Exception as e:
        print(f"OpenRouter error: {e}")
        return {
            "clause_analysis": [],
            "missing_clauses": [],
            "overall_risk": "Error",
            "executive_summary": f"Analysis failed: {str(e)}"
        }

# -------------------------------
# History endpoints
# -------------------------------
@app.get("/history")
async def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
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
async def get_analysis(analysis_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    analysis = db.query(ContractAnalysis).filter(ContractAnalysis.id == analysis_id, ContractAnalysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return json.loads(analysis.analysis_json)

@app.delete("/history/{analysis_id}")
async def delete_analysis(analysis_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    analysis = db.query(ContractAnalysis).filter(ContractAnalysis.id == analysis_id, ContractAnalysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.delete(analysis)
    db.commit()
    return {"message": "Deleted"}

# -------------------------------
# Health check (public)
# -------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}