# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.
# ===================================================================

import os
import json
import sqlite3
import jwt
import hashlib
import hmac
import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, File, Form, UploadFile, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import openai
import httpx
from pydantic import BaseModel

# ---------- Configuration ----------
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
DATABASE_URL = "lexsarthi.db"

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your-openrouter-key")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

app = FastAPI(title="LexSarthi API", version="2.0")

# CORS - allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ---------- Database Setup ----------
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent TEXT NOT NULL,
            input_text TEXT,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT,
            consent BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Helper Functions ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ---------- Models ----------
class UserRegister(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ContactForm(BaseModel):
    name: str
    email: str
    subject: str
    message: str
    consent: bool = True

class RunAgentRequest(BaseModel):
    agent_name: str
    text: Optional[str] = None
    # file handled via UploadFile separately

# ---------- Agents List (16 agents) ----------
AGENTS = [
    {"id": "contract_review", "name": "Contract Review", "icon": "📄", "description": "Analyse contracts for risks, missing clauses, and redlines."},
    {"id": "due_diligence", "name": "Due Diligence", "icon": "🔍", "description": "M&A due diligence, identify legal red flags."},
    {"id": "legal_research", "name": "Legal Research", "icon": "📚", "description": "Research case law, statutes, and legal principles."},
    {"id": "domain_review", "name": "Domain Review", "icon": "🌐", "description": "Review domain name disputes and trademark issues."},
    {"id": "nda", "name": "NDA Analysis", "icon": "🤝", "description": "Analyse non-disclosure agreements."},
    {"id": "employment", "name": "Employment Contract", "icon": "👔", "description": "Review employment agreements and HR policies."},
    {"id": "ip", "name": "Intellectual Property", "icon": "💡", "description": "IP registration, licensing, and infringement analysis."},
    {"id": "tax", "name": "Tax Structuring", "icon": "💰", "description": "Tax planning, GST, and compliance."},
    {"id": "compliance", "name": "Regulatory Compliance", "icon": "✅", "description": "Check compliance with DPDP, GDPR, IBC, etc."},
    {"id": "litigation", "name": "Litigation Risk", "icon": "⚖️", "description": "Assess litigation risks and strategy."},
    {"id": "corporate", "name": "Corporate Governance", "icon": "🏢", "description": "Board resolutions, shareholder agreements."},
    {"id": "real_estate", "name": "Real Estate", "icon": "🏠", "description": "Property agreements, title verification."},
    {"id": "finance", "name": "Finance & Banking", "icon": "🏦", "description": "Loan agreements, security documents."},
    {"id": "data_protection", "name": "Data Protection", "icon": "🔒", "description": "DPDP Act, GDPR, privacy policies."},
    {"id": "insolvency", "name": "Insolvency & Bankruptcy", "icon": "📉", "description": "IBC, insolvency risk assessment."},
    {"id": "arbitration", "name": "Arbitration & Dispute", "icon": "⚡", "description": "Arbitration clauses and dispute resolution."}
]

# ---------- Endpoints ----------

# 1. Health check (replaces the broken / route)
@app.get("/")
async def root():
    return {"status": "LexSarthi API is live", "version": "2.0"}

# 2. List agents
@app.get("/agents")
async def list_agents():
    return AGENTS

# 3. Run agent (supports file upload and text)
@app.post("/run-agent")
async def run_agent(
    request: Request,
    agent_name: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    token: str = Depends(oauth2_scheme)  # optional, can be made optional
):
    # Validate agent exists
    agent = next((a for a in AGENTS if a["id"] == agent_name), None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_name}")

    # Get input text from file or direct text
    input_text = text
    if file:
        contents = await file.read()
        try:
            input_text = contents.decode("utf-8")
        except:
            input_text = contents.decode("latin-1")

    if not input_text:
        raise HTTPException(status_code=400, detail="No input text provided")

    # Call OpenRouter AI
    try:
        # Build prompt based on agent type
        system_prompt = f"""
You are a senior legal expert specialising in {agent_name}. 
Analyse the following document and provide a structured output with:
1. "executive_summary": a brief summary
2. "overall_risk": "High", "Medium", or "Low"
3. "clause_analysis": list of objects with clause_number, clause_text, risk_level, legal_basis, reason, redline (suggested change)
4. "missing_clauses": list of objects with title, legal_basis, reason, proposed_clause_text
5. "lawyer_review": object with reviewed_by, experience, areas, qualification, review_date (ISO), note

Output in JSON format only.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document:\n{input_text}"}
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",  # or any other
                    "messages": messages,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)

            data = response.json()
            result = json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

    # Save history if user is authenticated (token provided)
    user = None
    try:
        user = get_current_user(token)
        conn = get_db()
        conn.execute(
            "INSERT INTO history (user_id, agent, input_text, result_json) VALUES (?, ?, ?, ?)",
            (user["id"], agent_name, input_text[:500], json.dumps(result))
        )
        conn.commit()
        conn.close()
    except:
        # If token invalid, just don't save history
        pass

    return result

# 4. Authentication - Register
@app.post("/auth/register")
async def register(user_data: UserRegister):
    conn = get_db()
    # Check if user exists
    existing = conn.execute("SELECT * FROM users WHERE username = ?", (user_data.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(user_data.password)
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)",
        (user_data.username, hashed, user_data.full_name)
    )
    conn.commit()
    conn.close()

    # Create token
    token = create_access_token({"sub": user_data.username})
    return {"access_token": token, "token_type": "bearer"}

# 5. Authentication - Login
@app.post("/auth/login")
async def login(user_data: UserLogin):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (user_data.username,)).fetchone()
    conn.close()
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user_data.username})
    return {"access_token": token, "token_type": "bearer"}

# 6. History (requires authentication)
@app.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT agent, input_text, result_json, created_at FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (current_user["id"],)
    ).fetchall()
    conn.close()
    history = []
    for r in rows:
        history.append({
            "agent": r["agent"],
            "input_text": r["input_text"],
            "result_json": json.loads(r["result_json"]),
            "created_at": r["created_at"]
        })
    return history

# 7. Contact form
@app.post("/contact")
async def contact(form: ContactForm):
    conn = get_db()
    conn.execute(
        "INSERT INTO contacts (name, email, subject, message, consent) VALUES (?, ?, ?, ?, ?)",
        (form.name, form.email, form.subject, form.message, form.consent)
    )
    conn.commit()
    conn.close()
    return {"message": "Thank you for contacting us. We will respond within 24 hours."}

# 8. Campaigns stub (to avoid 404)
@app.get("/campaigns")
async def campaigns():
    return {
        "emails_sent": 247,
        "opened": 89,
        "interested": 34,
        "pilots_signed": 12
    }

# ---------- Run with Uvicorn ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)