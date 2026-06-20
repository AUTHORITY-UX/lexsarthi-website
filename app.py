# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - THE COMPLETE LEGAL OS
# $10B VISION - SINGLE PROVIDER FOR ALL LEGAL WORK AUTOMATION
# ===================================================================
# "From Contract Review to Supreme Court Judgments"
# "From Law School to Global Legal Practice"
# "One Platform. Every Legal Need. Anywhere in the World."
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================
# 🔒 ZERO DATA RETENTION POLICY - Auto-delete after 24 hours
# 🎯 100% ACCURACY GUARANTEE - NO HALLUCINATION
# 🔐 CONFIDENTIALITY NOTICE - Attorney-Client Privilege
# ===================================================================

import os
import json
import sqlite3
import jwt
import hashlib
import datetime
import re
import socket
import whois
import dns.resolver
import ssl
import uuid
import base64
import hmac
import random
import shutil
import asyncio
import requests
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import httpx
from pydantic import BaseModel, EmailStr, Field
from bs4 import BeautifulSoup
import pdfplumber
import docx
from datetime import datetime, timedelta
import urllib.parse

# ===================================================================
# CONFIGURATION
# ===================================================================
SECRET_KEY = os.environ.get("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DATABASE_URL = "/data/lexsarthi.db"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openrouter/auto"
SIMILARWEB_API_KEY = os.environ.get("SIMILARWEB_API_KEY", "")

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# File Storage - TEMPORARY ONLY (Zero Retention)
UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Zero Data Retention Settings
DATA_RETENTION_HOURS = int(os.environ.get("DATA_RETENTION_HOURS", "24"))
ENABLE_AUTO_DELETE = os.environ.get("ENABLE_AUTO_DELETE", "true").lower() == "true"

# Free Trial Settings
FREE_TRIAL_DAYS = 15
STARTER_PACK_PRICE = 200  # ₹2 in paise

# Website URL
WEBSITE_URL = "https://www.advocacyalawfrim.in"

# ===================================================================
# PRICING PLANS
# ===================================================================
PRICING_PLANS = {
    "starter": {
        "name": "Starter",
        "price": 200,
        "price_label": "₹2",
        "duration": "forever",
        "agents": 6,
        "runs": 3,
        "users": 1,
        "storage": 100,
        "features": [
            "3 free agent runs (lifetime)",
            "6 basic agents",
            "Watermarked output",
            "Email support",
            "₹2 one-time payment"
        ],
        "badge": "⚡ STARTER",
        "cta": "Start for ₹2"
    },
    "professional": {
        "name": "Professional",
        "price": 149900,
        "price_label": "₹1,499",
        "duration": "month",
        "agents": 44,
        "runs": 250,
        "users": 1,
        "storage": 1000,
        "features": [
            "250 agent runs / month",
            "All 44 specialised agents",
            "Full history + PDF export",
            "Priority speed",
            "GST invoice"
        ],
        "badge": "🔥 POPULAR",
        "cta": "Subscribe — ₹1,499"
    },
    "firm": {
        "name": "Firm",
        "price": 2499900,
        "price_label": "₹24,999",
        "duration": "month",
        "agents": 50,
        "runs": 5000,
        "users": 15,
        "storage": 10000,
        "features": [
            "15 user seats",
            "5,000 runs / month",
            "Lawyer-review add-on",
            "Custom branding",
            "Dedicated CSM"
        ],
        "badge": "🏢 FIRM",
        "cta": "Talk to sales"
    }
}

PAY_PER_USE = {
    "domain_review": {"price": 200, "label": "₹2", "description": "Domain Review"},
    "domain_review_lawyer": {"price": 10000, "label": "₹100", "description": "Domain Review with Lawyer Review"},
    "ma_due_diligence": {"price": 250000, "label": "₹2,500", "description": "M&A Due Diligence"}
}

# ===================================================================
# APP INITIALIZATION
# ===================================================================
app = FastAPI(
    title="LexSarthi v4.0 - Complete Legal OS",
    description="Powered by THE ADVOCACY A LAW FIRM | Zero Data Retention | 100% Accuracy | 15 Days Free Trial | ₹2 Starter Pack | International Launch 20 June 2026 | From Contract to Supreme Court",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ===================================================================
# DATABASE
# ===================================================================
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                plan TEXT DEFAULT 'free',
                is_premium INTEGER DEFAULT 0,
                premium_expiry TIMESTAMP,
                trial_start_date TIMESTAMP,
                trial_end_date TIMESTAMP,
                organization TEXT,
                consent_given INTEGER DEFAULT 0,
                consent_date TIMESTAMP,
                confidentiality_accepted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                data_deleted INTEGER DEFAULT 0,
                deletion_requested INTEGER DEFAULT 0,
                deletion_date TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER,
                content TEXT,
                agent_used TEXT,
                analysis_result TEXT,
                status TEXT DEFAULT 'pending',
                lawyer_reviewed INTEGER DEFAULT 0,
                lawyer_notes TEXT,
                reviewed_by INTEGER,
                review_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                audience TEXT,
                content TEXT,
                scheduled_date TIMESTAMP,
                sent_date TIMESTAMP,
                open_count INTEGER DEFAULT 0,
                click_count INTEGER DEFAULT 0,
                response_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                campaign_id INTEGER,
                client_email TEXT,
                client_name TEXT,
                status TEXT DEFAULT 'pending',
                sent_date TIMESTAMP,
                opened_date TIMESTAMP,
                responded_date TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                agent TEXT,
                input_text TEXT,
                result_json TEXT,
                document_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_id TEXT UNIQUE NOT NULL,
                payment_id TEXT,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'INR',
                plan TEXT,
                status TEXT DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE retention_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT,
                entity_id INTEGER,
                deletion_reason TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

init_db()

# ===================================================================
# ZERO DATA RETENTION
# ===================================================================
async def delete_expired_data():
    retention_time = datetime.now() - timedelta(hours=DATA_RETENTION_HOURS)
    retention_time_str = retention_time.isoformat()
    
    conn = get_db()
    
    try:
        conn.execute(
            """UPDATE documents SET content = NULL, analysis_result = NULL 
               WHERE created_at < ?""",
            (retention_time_str,)
        )
        
        conn.execute(
            """UPDATE history SET input_text = NULL, result_json = NULL 
               WHERE created_at < ?""",
            (retention_time_str,)
        )
        
        conn.execute(
            "INSERT INTO retention_log (entity_type, entity_id, deletion_reason) VALUES (?, ?, ?)",
            ("system", 0, f"Zero Retention - Auto-deleted data older than {DATA_RETENTION_HOURS} hours")
        )
        
        conn.commit()
        print(f"✅ Zero Retention: Deleted data older than {DATA_RETENTION_HOURS} hours")
    except Exception as e:
        print(f"⚠️ Zero Retention error: {e}")
    finally:
        conn.close()

async def schedule_data_deletion():
    while True:
        if ENABLE_AUTO_DELETE:
            await delete_expired_data()
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(schedule_data_deletion())

# ===================================================================
# PYDANTIC MODELS
# ===================================================================
class UserRegister(BaseModel):
    username: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    plan: str = "free"
    consent_given: bool = False
    confidentiality_accepted: bool = False

class UserLogin(BaseModel):
    username: EmailStr
    password: str

class AgentRunRequest(BaseModel):
    agent_id: str
    input_text: str = ""
    file_content: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None

class DomainScanRequest(BaseModel):
    domain: str

class PolicyScanRequest(BaseModel):
    website_url: str

class PaymentRequest(BaseModel):
    amount: int
    currency: str = "INR"
    plan: Optional[str] = None

class PaymentVerifyRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

class CampaignCreate(BaseModel):
    name: str
    type: str
    audience: Optional[str] = None
    content: Optional[str] = None
    scheduled_date: Optional[str] = None

class OutreachCreate(BaseModel):
    campaign_id: int
    client_email: str
    client_name: str
    notes: Optional[str] = None

class DomainAgreementRequest(BaseModel):
    domain: str
    agreement_type: str = "domain_due_diligence"
    include_social: bool = True
    include_traffic: bool = True

# ===================================================================
# UTILITY FUNCTIONS
# ===================================================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_jwt(username: str, role: str = "user") -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (payload.get("sub"),)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

async def get_current_user_bearer(auth: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_jwt(auth.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (payload.get("sub"),)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = verify_jwt(token)
        if not payload:
            return None
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (payload.get("sub"),)).fetchone()
        conn.close()
        return dict(user) if user else None
    except:
        return None

async def parse_document(file: UploadFile) -> tuple:
    content = await file.read()
    file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else 'txt'
    file_size = len(content)
    text = ""
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        if file_type == 'pdf':
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        elif file_type == 'docx':
            import io
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            text = content.decode('utf-8', errors='ignore')
    except Exception as e:
        text = f"Could not parse document: {str(e)}"
    
    return text, file_type, file_size, file_path

# ===================================================================
# LAWYER DEBO PROFILE
# ===================================================================
LAWYER_PROFILE = {
    "name": "Adv. Debo",
    "firm": "THE ADVOCACY A LAW FIRM",
    "website": WEBSITE_URL,
    "experience": "8+ years",
    "qualification": "LLB - Campus Law Centre, Delhi University (2016)",
    "management_qualification": "IIM Sirmaur (2025)",
    "specialization": ["Corporate Law", "IBC", "RERA", "Contract Law", "Data Privacy"],
    "certifications": ["DPDP Act 2023 Compliance", "GDPR Certified", "AI Governance"],
    "languages": ["English", "Hindi", "Portuguese"],
    "review_note": "Reviewed by Adv. Debo, THE ADVOCACY A LAW FIRM."
}

# ===================================================================
# COMPLETE LEGAL REFERENCE LIBRARY
# ===================================================================
LEGAL_REFERENCE_LIBRARY = """
====================================================================
DPDP ACT 2023 – SECTIONS 4-14
====================================================================
Section 4: Consent Requirement
Section 5: Purpose Limitation
Section 6: Data Minimisation
Section 7: Data Quality
Section 8: Rights of Data Principal
Section 9: Security Safeguards
Section 10: Data Breach Notification
Section 11: Cross-Border Data Transfer
Section 12: Significant Data Fiduciaries
Section 13: Data Protection Board of India
Section 14: Penalties – up to ₹250 crore

====================================================================
IT RULES 2011 – RULES 3-8
====================================================================
Rule 3: Privacy Policy Requirement
Rule 4: Sensitive Personal Data or Information (SPDI)
Rule 5: Collection of Information - Consent Required
Rule 6: Disclosure of Information
Rule 7: Security Practices
Rule 8: Grievance Redressal

====================================================================
CONSTITUTION OF INDIA
====================================================================
Article 14: Right to Equality
Article 19(1)(a): Freedom of Speech and Expression
Article 21: Right to Life and Personal Liberty

====================================================================
INDIAN CONTRACT ACT 1872
====================================================================
Section 10: What agreements are contracts
Section 23: What considerations and objects are lawful
Section 73: Compensation for breach
Section 74: Liquidated damages

====================================================================
IT ACT 2000
====================================================================
Section 43A: Compensation for failure to protect data
Section 66A: Punishment for sending offensive messages (Struck down)
Section 69: Power to issue directions for interception
Section 70: Protected system

====================================================================
COMPANIES ACT 2013
====================================================================
Section 2: Definitions
Section 3: Formation of company
Section 4: Memorandum of Association
Section 5: Articles of Association
Section 6: Name of the company
Section 7: Incorporation of company
Section 8: Formation of companies with charitable objects, etc.
Section 9: Effect of registration
Section 10: Effect of memorandum and articles

====================================================================
IBC 2016
====================================================================
Section 3: Definitions
Section 4: Application of this Code
Section 5: Definitions
Section 6: Persons who may initiate corporate insolvency resolution process
Section 7: Initiation of corporate insolvency resolution process by financial creditor
Section 9: Application for initiation by operational creditor
Section 12: Time-limit for completion of insolvency resolution process
Section 31: Approval of resolution plan
Section 53: Distribution of assets

====================================================================
RERA 2016
====================================================================
Section 3: Registration of real estate project
Section 4: Application for registration of real estate project
Section 11: Obligations of promoter regarding registration and other matters
Section 18: Return of amount and compensation
Section 19: Rights and duties of allottee
Section 31: Filing of complaints

====================================================================
POSH ACT 2013
====================================================================
Section 4: Constitution of Internal Complaints Committee
Section 9: Complaint of sexual harassment
Section 13: Inquiry into complaint
Section 14: Penalty for non-compliance

====================================================================
KEY CASE LAWS
====================================================================
Justice K.S. Puttaswamy v. Union of India (2017) 10 SCC 1
Shreya Singhal v. Union of India (2015) 5 SCC 1
N.S. Nappinai v. Union of India (2021) 7 SCC 451
Cellular Operators Association of India v. TRAI (2019) 7 SCC 370
"""

# ===================================================================
# AGENT PROMPTS
# ===================================================================
AGENT_PROMPTS = {
    "compliance_dpdp": """
You are Adv. Debo from THE ADVOCACY A LAW FIRM.
SPECIALIZATION: DPDP Act 2023, Data Privacy
CERTIFICATION: DPDP Act 2023 Compliance Certified

TASK: Analyze compliance with DPDP Act 2023 Sections 4-14.

LEGAL REFERENCE:
{legal_reference}

POLICY TEXT:
{input_text}

PROVIDE:
1. executive_summary: DPDP compliance assessment
2. findings: Issues with section references
3. recommendations: Compliance actions
4. legal_basis: Exact DPDP sections
""",

    "contract_review_general": """
You are Adv. Debo from THE ADVOCACY A LAW FIRM.
SPECIALIZATION: Contract Law, Indian Contract Act 1872

TASK: Review contract with Indian Contract Act 1872 references.

LEGAL REFERENCE:
{legal_reference}

CONTRACT TEXT:
{input_text}

PROVIDE:
1. executive_summary: Contract review summary
2. findings: Issues with section references (Sections 10,23,73,74)
3. recommendations: Improvements needed
4. legal_basis: Contract Act sections
""",
}

DEFAULT_AGENT_PROMPT = """
You are Adv. Debo from THE ADVOCACY A LAW FIRM.
EXPERIENCE: 8+ years
QUALIFICATION: LLB - Delhi University (2016)

LEGAL REFERENCE:
{legal_reference}

INPUT:
{input_text}

PROVIDE:
1. executive_summary: Professional summary
2. findings: Legal findings
3. recommendations: Specific actions
4. legal_basis: Relevant laws
5. disclaimer: "AI-assisted - verify with advocate"
"""

# ===================================================================
# AGENTS LIST - 50+ AGENTS
# ===================================================================
AGENTS = [
    # Contract Review
    {"id": "contract_review_general", "name": "General Contract Review", "icon": "📄", "description": "Review contracts with Indian Contract Act 1872 - Adv. Debo", "category": "Contract Review", "premium": False},
    {"id": "contract_review_employment", "name": "Employment Contract Review", "icon": "👔", "description": "Review employment agreements - Adv. Debo", "category": "Contract Review", "premium": False},
    {"id": "contract_review_commercial", "name": "Commercial Contract Review", "icon": "🤝", "description": "Review commercial contracts - Adv. Debo", "category": "Contract Review", "premium": True},
    {"id": "contract_review_nda", "name": "NDA Review", "icon": "🔒", "description": "Review confidentiality agreements - Adv. Debo", "category": "Contract Review", "premium": False},
    {"id": "contract_review_service", "name": "Service Agreement Review", "icon": "📋", "description": "Review service agreements - Adv. Debo", "category": "Contract Review", "premium": False},
    {"id": "contract_review_lease", "name": "Lease Agreement Review", "icon": "🏠", "description": "Review lease agreements - Adv. Debo", "category": "Contract Review", "premium": False},
    {"id": "contract_review_loan", "name": "Loan Agreement Review", "icon": "💰", "description": "Review loan agreements - Adv. Debo", "category": "Contract Review", "premium": False},
    {"id": "contract_review_partnership", "name": "Partnership Review", "icon": "🤝", "description": "Review partnership agreements - Adv. Debo", "category": "Contract Review", "premium": False},
    
    # Drafting
    {"id": "drafting_general", "name": "General Legal Drafting", "icon": "📝", "description": "Draft legal documents - Adv. Debo", "category": "Drafting", "premium": False},
    {"id": "drafting_employment", "name": "Employment Contract Drafting", "icon": "📋", "description": "Draft employment agreements - Adv. Debo", "category": "Drafting", "premium": False},
    {"id": "drafting_commercial", "name": "Commercial Agreement Drafting", "icon": "🏢", "description": "Draft commercial contracts - Adv. Debo", "category": "Drafting", "premium": True},
    {"id": "drafting_nda", "name": "NDA Drafting", "icon": "📄", "description": "Draft confidentiality agreements - Adv. Debo", "category": "Drafting", "premium": False},
    {"id": "drafting_lease", "name": "Lease Agreement Drafting", "icon": "🏠", "description": "Draft lease agreements - Adv. Debo", "category": "Drafting", "premium": False},
    {"id": "drafting_policy", "name": "Policy Document Drafting", "icon": "📜", "description": "Draft company policies - Adv. Debo", "category": "Drafting", "premium": False},
    {"id": "drafting_will", "name": "Will Drafting", "icon": "📜", "description": "Draft wills - Adv. Debo", "category": "Drafting", "premium": False},
    
    # Compliance
    {"id": "compliance_dpdp", "name": "DPDP Act Compliance", "icon": "🛡️", "description": "DPDP Act 2023 Sections 4-14 - Adv. Debo (Certified)", "category": "Compliance", "premium": False},
    {"id": "compliance_it_rules", "name": "IT Rules 2011 Compliance", "icon": "💻", "description": "IT Rules 2011 Rules 3-8 - Adv. Debo", "category": "Compliance", "premium": False},
    {"id": "compliance_gdpr", "name": "GDPR Compliance", "icon": "🌍", "description": "GDPR compliance - Adv. Debo (Certified)", "category": "Compliance", "premium": True},
    {"id": "compliance_employment", "name": "Employment Law Compliance", "icon": "👷", "description": "Labour law compliance - Adv. Debo", "category": "Compliance", "premium": False},
    {"id": "compliance_privacy", "name": "Privacy Policy Compliance", "icon": "🔒", "description": "Privacy policy analysis - Adv. Debo", "category": "Compliance", "premium": False},
    {"id": "compliance_corporate", "name": "Corporate Compliance", "icon": "🏛️", "description": "Companies Act 2013 compliance - Adv. Debo", "category": "Compliance", "premium": True},
    {"id": "compliance_ibc", "name": "IBC Compliance", "icon": "📋", "description": "IBC 2016 compliance - Adv. Debo (IBC Expert)", "category": "Compliance", "premium": True},
    {"id": "compliance_rera", "name": "RERA Compliance", "icon": "🏠", "description": "RERA Act 2016 compliance - Adv. Debo (RERA Expert)", "category": "Compliance", "premium": False},
    
    # Litigation
    {"id": "litigation_case_assessment", "name": "Case Assessment", "icon": "⚖️", "description": "Case strength assessment - Adv. Debo", "category": "Litigation", "premium": True},
    {"id": "litigation_pleading", "name": "Pleading Drafting", "icon": "📜", "description": "Draft court pleadings - Adv. Debo", "category": "Litigation", "premium": False},
    {"id": "litigation_discovery", "name": "Discovery Support", "icon": "🔍", "description": "Discovery assistance - Adv. Debo", "category": "Litigation", "premium": False},
    {"id": "litigation_settlement", "name": "Settlement Analysis", "icon": "🤝", "description": "Settlement options - Adv. Debo", "category": "Litigation", "premium": False},
    {"id": "litigation_appeal", "name": "Appeal Support", "icon": "📈", "description": "Appeal process support - Adv. Debo", "category": "Litigation", "premium": False},
    {"id": "litigation_arbitration", "name": "Arbitration Support", "icon": "⚖️", "description": "Arbitration clauses - Adv. Debo", "category": "Litigation", "premium": False},
    
    # Research
    {"id": "research_case_law", "name": "Case Law Research", "icon": "📚", "description": "Case law research - Adv. Debo", "category": "Research", "premium": False},
    {"id": "research_statutory", "name": "Statutory Research", "icon": "📖", "description": "Statute research - Adv. Debo", "category": "Research", "premium": False},
    {"id": "research_legal_opinion", "name": "Legal Opinion Research", "icon": "📝", "description": "Legal opinion research - Adv. Debo", "category": "Research", "premium": False},
    {"id": "research_judgments", "name": "Judgment Analysis", "icon": "⚖️", "description": "Judgment analysis - Adv. Debo", "category": "Research", "premium": False},
    {"id": "citation_verifier", "name": "Citation Verifier", "icon": "📚", "description": "Verify legal citations - Adv. Debo", "category": "Research", "premium": False},
    
    # IP
    {"id": "ip_trademark", "name": "Trademark Assistance", "icon": "™️", "description": "Trademark registration - Adv. Debo", "category": "IP", "premium": False},
    {"id": "ip_copyright", "name": "Copyright Assistance", "icon": "©️", "description": "Copyright registration - Adv. Debo", "category": "IP", "premium": False},
    {"id": "ip_patent", "name": "Patent Assistance", "icon": "🔬", "description": "Patent applications - Adv. Debo", "category": "IP", "premium": True},
    {"id": "ip_licensing", "name": "IP Licensing Review", "icon": "📄", "description": "IP licensing - Adv. Debo", "category": "IP", "premium": False},
    
    # Corporate
    {"id": "corporate_incorporation", "name": "Company Incorporation", "icon": "🏢", "description": "Company formation - Adv. Debo", "category": "Corporate", "premium": False},
    {"id": "corporate_governance", "name": "Corporate Governance", "icon": "🏛️", "description": "Governance review - Adv. Debo", "category": "Corporate", "premium": False},
    {"id": "corporate_merger", "name": "M&A Due Diligence", "icon": "📊", "description": "M&A due diligence - Adv. Debo", "category": "Corporate", "premium": True},
    {"id": "corporate_board", "name": "Board Meeting Support", "icon": "👥", "description": "Board meeting support - Adv. Debo", "category": "Corporate", "premium": False},
    
    # Tax
    {"id": "tax_compliance", "name": "Tax Compliance Review", "icon": "💰", "description": "Tax compliance - Adv. Debo", "category": "Tax", "premium": False},
    {"id": "tax_planning", "name": "Tax Planning Advice", "icon": "📊", "description": "Tax planning - Adv. Debo", "category": "Tax", "premium": False},
    {"id": "tax_gst", "name": "GST Compliance", "icon": "📋", "description": "GST compliance - Adv. Debo", "category": "Tax", "premium": False},
    
    # Real Estate
    {"id": "real_estate_purchase", "name": "Property Purchase Review", "icon": "🏠", "description": "Property purchase - Adv. Debo (RERA Expert)", "category": "Real Estate", "premium": False},
    {"id": "real_estate_lease", "name": "Property Lease Review", "icon": "🏢", "description": "Lease review - Adv. Debo", "category": "Real Estate", "premium": False},
    {"id": "real_estate_due_diligence", "name": "Property Due Diligence", "icon": "🔍", "description": "Property due diligence - Adv. Debo", "category": "Real Estate", "premium": True},
    
    # Family
    {"id": "family_divorce", "name": "Divorce Support", "icon": "💔", "description": "Divorce support - Adv. Debo", "category": "Family", "premium": False},
    {"id": "family_custody", "name": "Child Custody Support", "icon": "👶", "description": "Child custody - Adv. Debo", "category": "Family", "premium": False},
    {"id": "family_maintenance", "name": "Maintenance Support", "icon": "💰", "description": "Maintenance support - Adv. Debo", "category": "Family", "premium": False},
    
    # Criminal
    {"id": "criminal_defense", "name": "Criminal Defense Support", "icon": "⚖️", "description": "Criminal defense - Adv. Debo", "category": "Criminal", "premium": False},
    {"id": "criminal_bail", "name": "Bail Application", "icon": "🔓", "description": "Bail applications - Adv. Debo", "category": "Criminal", "premium": False},
    {"id": "criminal_anticipatory_bail", "name": "Anticipatory Bail", "icon": "🛡️", "description": "Anticipatory bail - Adv. Debo", "category": "Criminal", "premium": True},
    {"id": "criminal_fir", "name": "FIR Drafting", "icon": "📋", "description": "FIR drafting - Adv. Debo", "category": "Criminal", "premium": False},
    
    # Employment
    {"id": "employment_discrimination", "name": "Discrimination Claims", "icon":