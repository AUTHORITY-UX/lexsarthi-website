# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os
import csv
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

from agents import get_agent
from verifier import VerifierAgent
from schemas import LegalAgentOutput

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

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- FastAPI App ----------
app = FastAPI(title="Lexsarthi Automation OS")

# Enable CORS (if not already present)
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
        sender = os.getenv("SMTP_EMAIL", "test@lexsarthi.com")
        password = os.getenv("SMTP_PASSWORD", "")
        server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        port = int(os.getenv("SMTP_PORT", 587))
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to
        part = MIMEText(html_body, 'html')
        msg.attach(part)
        
        with smtplib.SMTP(server, port) as smtp:
            smtp.starttls()
            if password:
                smtp.login(sender, password)
            smtp.sendmail(sender, to, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ---------- Routes ----------

# Serve the new dashboard at the root
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse("templates/index.html")

# Agent with built-in Verifier
@app.post("/run-agent-verified")
async def run_agent_verified(request: Request, db: Session = Depends(get_db)):
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

# Outreach: Leads
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

# Outreach: Campaigns
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

@app.get("/health")
async def health():
    return {"status": "Lexsarthi OS running", "mode": "Production with Verifier"}

# ---------- Your existing routes (like /login, /signup, /contact, /agents, etc.) should be placed here ----------
# If you already have them, keep them as they are; just ensure they don't conflict with /, /run-agent-verified, /api/...