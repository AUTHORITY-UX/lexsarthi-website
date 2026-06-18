# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os
import csv
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, File, UploadFile, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import uuid

# ---------- Configuration ----------
class Settings:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_DEFAULT_MODEL = "openai/gpt-4o"
    LOCAL_LLM_ENABLED = os.getenv("LOCAL_LLM_ENABLED", "false").lower() == "true"
    LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:8000/v1")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    LOCAL_EMBEDDING_ENABLED = os.getenv("LOCAL_EMBEDDING_ENABLED", "false").lower() == "true"
    LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-m3")
    USE_LOCAL_PRIMARY = os.getenv("USE_LOCAL_PRIMARY", "false").lower() == "true"
    FALLBACK_TO_OPENROUTER = os.getenv("FALLBACK_TO_OPENROUTER", "true").lower() == "true"
    SITE_URL = os.getenv("SITE_URL", "http://localhost:7860")
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-me")
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

settings = Settings()

# ---------- Database Setup ----------
SQLALCHEMY_DATABASE_URL = "sqlite:///./lexsarthi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------- Models (Tables) ----------
class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    company = Column(String, default="")
    title = Column(String, default="")
    segment = Column(String, default="general")
    status = Column(String, default="new")
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body_template = Column(Text, nullable=False)
    segment = Column(String, default="all")
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_count = Column(Integer, default=0)

class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer)
    campaign_id = Column(Integer)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="sent")
    error_message = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- FastAPI App ----------
app = FastAPI(title="LexSarthi OS", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helper: SMTP Email ----------
def send_smtp_email(to: str, subject: str, html_body: str) -> bool:
    try:
        if not settings.SMTP_EMAIL:
            print("SMTP_EMAIL not set, skipping email send")
            return False
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.SMTP_EMAIL
        msg['To'] = to
        part = MIMEText(html_body, 'html')
        msg.attach(part)
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtp:
            smtp.starttls()
            if settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.SMTP_EMAIL, to, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ---------- Agent Imports & Logic ----------
# We'll use your existing agents.py and verifier.py
from agents import get_agent
from verifier import VerifierAgent
from schemas import LegalAgentOutput

# ---------- Endpoint: Serve Frontend (optional) ----------
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    try:
        return FileResponse("templates/index.html")
    except Exception:
        return HTMLResponse("<h1>LexSarthi OS is running</h1><p>API is live. Visit /agents to see the agent list.</p>")

# ---------- GET /agents ----------
@app.get("/agents")
async def get_agents():
    agents = [
        {"id": "contract_risk", "name": "CONTRACT RISK", "description": "Analyzes contracts for risk clauses, missing terms, and compliance issues.", "category": "Risk & Compliance"},
        {"id": "legal_notice", "name": "LEGAL NOTICE", "description": "Drafts and reviews legal notices for various scenarios.", "category": "Drafting"},
        {"id": "nda_triage", "name": "NDA TRIAGE", "description": "Reviews NDAs, flags unusual clauses, and suggests redlines.", "category": "Contracts"},
        {"id": "consent_form", "name": "CONSENT FORM", "description": "Analyzes consent forms for regulatory compliance.", "category": "Compliance"},
        {"id": "oral_arguments", "name": "ORAL ARGUMENTS", "description": "Prepares oral argument outlines based on case law and facts.", "category": "Litigation"},
        {"id": "employment_law", "name": "EMPLOYMENT LAW", "description": "Reviews employment contracts, policies, and termination clauses.", "category": "Employment"},
        {"id": "dpdp_check", "name": "DPDP CHECK", "description": "Ensures compliance with India's DPDP Act, 2023.", "category": "Compliance"},
        {"id": "due_diligence", "name": "DUE DILIGENCE", "description": "Performs legal due diligence for M&A and investments.", "category": "M&A"},
        {"id": "weekly_digest", "name": "WEEKLY DIGEST", "description": "Summarizes recent legal updates and case law.", "category": "Research"},
        {"id": "domain_review", "name": "DOMAIN REVIEW", "description": "Reviews intellectual property domains for risks.", "category": "IP"},
        {"id": "ma_due_diligence", "name": "MA DUE DILIGENCE", "description": "Specialized due diligence for M&A transactions.", "category": "M&A"},
        {"id": "ip_filing", "name": "IP FILING", "description": "Assists with patent, trademark, and copyright filings.", "category": "IP"},
        {"id": "tax_compliance", "name": "TAX COMPLIANCE", "description": "Analyzes tax clauses and compliance requirements.", "category": "Tax"},
        {"id": "real_estate_review", "name": "REAL ESTATE REVIEW", "description": "Reviews property agreements, leases, and title documents.", "category": "Real Estate"},
        {"id": "competition_law", "name": "COMPETITION LAW", "description": "Identifies anti-competitive clauses and compliance gaps.", "category": "Regulatory"},
        {"id": "data_privacy", "name": "DATA PRIVACY", "description": "Checks data protection and privacy compliance (GDPR, DPDP).", "category": "Compliance"}
    ]
    return JSONResponse(content=agents)

# ---------- POST /run-agent (FIXED) ----------
@app.post("/run-agent")
async def run_agent(
    request: Request,
    agent_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    Runs the specified agent. Accepts both JSON (for backward compatibility) and form-data.
    """
    # Detect content type
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        data = await request.json()
        agent_name = data.get("agent_name")
        text = data.get("text") or data.get("document")
        file = None
    # If form-data, the parameters are already bound

    if not agent_name:
        raise HTTPException(400, "agent_name is required")
    
    content = ""
    if file:
        content = (await file.read()).decode("utf-8", errors="ignore")
    elif text:
        content = text
    else:
        raise HTTPException(400, "No input provided")

    # Call the agent
    try:
        agent = get_agent(agent_name)
        output: LegalAgentOutput = agent.run(content)
        return JSONResponse(content=output.model_dump())
    except Exception as e:
        return JSONResponse(
            content={"error": f"Agent execution failed: {str(e)}"},
            status_code=500
        )

# ---------- POST /run-agent-verified (with Verifier) ----------
@app.post("/run-agent-verified")
async def run_agent_verified(request: Request):
    data = await request.json()
    doc = data.get("document", "").strip()
    agent_type = data.get("agent_type", "contract_review")

    if not doc:
        return JSONResponse({"error": "No document provided"}, status_code=400)

    agent = get_agent(agent_type)
    output = agent.run(doc)
    verifier = VerifierAgent()
    is_valid, score, issues, badge = verifier.verify(output, doc)

    return {
        "output": output.model_dump(),
        "verification": {
            "valid": is_valid,
            "score": score,
            "issues": issues,
            "badge": badge
        }
    }

# ---------- Outreach API: Leads ----------
@app.post("/api/leads")
async def upload_leads(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")
    
    content = await file.read()
    stream = io.StringIO(content.decode("utf-8"), newline=None)
    csv_reader = csv.DictReader(stream)
    
    added = 0
    for row in csv_reader:
        email = row.get("email", "").strip()
        if not email:
            continue
        existing = db.query(Lead).filter(Lead.email == email).first()
        if existing:
            continue
        lead = Lead(
            email=email,
            first_name=row.get("first_name", ""),
            last_name=row.get("last_name", ""),
            company=row.get("company", ""),
            title=row.get("title", ""),
            segment=row.get("segment", "general")
        )
        db.add(lead)
        added += 1
    db.commit()
    return {"message": f"Added {added} leads"}

@app.get("/api/leads")
async def get_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).all()
    return [{
        "id": l.id,
        "email": l.email,
        "first_name": l.first_name,
        "company": l.company,
        "segment": l.segment,
        "status": l.status
    } for l in leads]

# ---------- Outreach API: Campaigns ----------
class CampaignCreate(BaseModel):
    name: str
    subject: str
    body_template: str
    segment: str = "all"

@app.post("/api/campaigns")
async def create_campaign(c: CampaignCreate, db: Session = Depends(get_db)):
    camp = Campaign(
        name=c.name,
        subject=c.subject,
        body_template=c.body_template,
        segment=c.segment,
        status="active"
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return {"id": camp.id, "message": "Campaign created"}

@app.get("/api/campaigns")
async def get_campaigns(db: Session = Depends(get_db)):
    camps = db.query(Campaign).all()
    return [{
        "id": c.id,
        "name": c.name,
        "subject": c.subject,
        "segment": c.segment,
        "status": c.status,
        "sent_count": c.sent_count
    } for c in camps]

@app.post("/api/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    query = db.query(Lead)
    if campaign.segment != "all":
        query = query.filter(Lead.segment == campaign.segment)
    leads = query.filter(Lead.status != "contacted").all()

    if not leads:
        return {"message": "No leads to send"}

    sent = 0
    for lead in leads:
        subject = campaign.subject.replace("{first_name}", lead.first_name or "").replace("{company}", lead.company or "")
        body = campaign.body_template.replace("{first_name}", lead.first_name or "").replace("{company}", lead.company or "")
        success = send_smtp_email(lead.email, subject, body)
        log = EmailLog(lead_id=lead.id, campaign_id=campaign.id, status="sent" if success else "failed")
        db.add(log)
        if success:
            lead.status = "contacted"
            sent += 1

    campaign.sent_count += sent
    db.commit()
    return {"message": f"Sent {sent} emails"}

# ---------- Health and Status ----------
@app.get("/health")
async def health():
    return {"status": "LexSarthi OS running", "mode": "Production with Verifier"}

@app.get("/api/status")
async def api_status():
    return JSONResponse(content={
        "status": "online",
        "agents_count": 16,
        "version": "2.0.0",
        "local_llm_enabled": settings.LOCAL_LLM_ENABLED,
        "openrouter_fallback": settings.FALLBACK_TO_OPENROUTER,
        "server": "LexSarthi OS"
    })

# ---------- Razorpay Webhook (optional) ----------
# Uncomment and configure if you want subscription automation
# @app.post("/webhook/razorpay")
# async def razorpay_webhook(request: Request):
#     body = await request.body()
#     signature = request.headers.get("X-Razorpay-Signature")
#     # Verify signature and process event
#     return {"status": "ok"}

# ---------- Run the App ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)