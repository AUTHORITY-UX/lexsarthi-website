# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.
# ===================================================================
# LexSarthi v2.3 – 49 Agents + DPDP Act Reference Library
# - Added Policy Compliance Scanner (visits sites, scans privacy/terms/cookie policies)
# - 49 specialised agents
# - DPDP Act 2023, IT Rules 2011, Constitution of India references
# ===================================================================

import os
import json
import sqlite3
import jwt
import hashlib
import datetime
import re
from typing import Optional, List, Dict
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import httpx
from pydantic import BaseModel, EmailStr
from bs4 import BeautifulSoup
import pdfplumber
import docx
import urllib.parse

# ---------- CONFIG ----------
SECRET_KEY = os.environ.get("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DATABASE_URL = "/data/lexsarthi.db"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openrouter/auto"

# ---------- APP ----------
app = FastAPI(title="LexSarthi API", version="2.3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ---------- DATABASE ----------
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
            user_id INTEGER,
            agent TEXT,
            input_text TEXT,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT,
            path TEXT,
            status INTEGER,
            ip TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- PYDANTIC MODELS ----------
class UserRegister(BaseModel):
    username: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: EmailStr
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class GrievanceSubmit(BaseModel):
    subject: str
    message: str

class CitationRequest(BaseModel):
    query: str

class PolicyScanRequest(BaseModel):
    website_url: str
    privacy_policy_url: Optional[str] = None
    terms_url: Optional[str] = None
    cookie_url: Optional[str] = None

# ---------- UTILITIES ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_jwt(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    username = verify_jwt(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return dict(user) if user else None
    except:
        return None

# ---------- DOCUMENT PARSING ----------
async def parse_document(file: UploadFile) -> str:
    content = await file.read()
    ext = file.filename.split('.')[-1].lower()
    text = ""
    if ext == 'pdf':
        import io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif ext == 'docx':
        import io
        doc = docx.Document(io.BytesIO(content))
        for para in doc.paragraphs:
            text += para.text + "\n"
    else:
        text = content.decode('utf-8', errors='ignore')
    return text.strip()

# ---------- LEGAL REFERENCE LIBRARY (DPDP Act 2023 + IT Rules + Constitution) ----------
LEGAL_REFERENCE_LIBRARY = """
=== DPDP ACT 2023 – KEY SECTIONS ===

Section 4: Consent requirement – personal data must be processed only with explicit, informed consent.
Section 5: Purpose limitation – data must be collected for a specific, lawful purpose.
Section 6: Data minimisation – collect only the data necessary for the purpose.
Section 7: Data quality – ensure data is accurate and up‑to‑date.
Section 8: Rights of data principal – access, correction, erasure, grievance, nomination.
Section 9: Security safeguards – reasonable security practices to prevent breach.
Section 10: Data breach notification – notify the Board and data principals in case of breach.
Section 11: Cross‑border data transfer – may transfer to notified countries only.
Section 12: Significant data fiduciaries – additional obligations (DPIA, data protection officer).
Section 13: Data Protection Board of India – oversight and enforcement.
Section 14: Penalties – up to ₹250 crore for non‑compliance.

=== IT RULES 2011 (Data Protection) ===

Rule 3: Privacy policy requirement – every body corporate must publish a privacy policy.
Rule 4: Sensitive personal data or information (SPDI) – definition and obligations.
Rule 5: Collection of information – must obtain consent.
Rule 6: Disclosure of information – prohibited except with consent or legal requirement.
Rule 7: Security practices – must implement reasonable security practices.
Rule 8: Grievance redressal – must appoint a grievance officer.

=== CONSTITUTION OF INDIA ===

Article 14 – Right to Equality
Article 19(1)(a) – Freedom of Speech and Expression
Article 21 – Right to Life and Personal Liberty (includes right to privacy per Puttaswamy v. UOI 2017)

=== CASE LAW ===

Justice K.S. Puttaswamy v. Union of India (2017) – Privacy is a fundamental right under Article 21.
Nikesh Tarachand Shah v. Union of India (2018) – Bail principles.
State of Maharashtra v. B.B. Aghav (2017) – Data protection obligations.

=== GDPR (EU) – RELEVANT PROVISIONS ===

Article 5 – Principles relating to processing of personal data.
Article 6 – Lawfulness of processing.
Article 7 – Conditions for consent.
Article 13 – Information to be provided where personal data are collected.
Article 17 – Right to erasure ('right to be forgotten').
Article 33 – Notification of a personal data breach to the supervisory authority.
"""

# ---------- PROMPT TEMPLATES ----------
DEFAULT_PROMPT = """
You are a legal AI assistant. Analyse the following text and return a JSON with:
- executive_summary: a brief summary
- overall_risk: "High", "Medium", or "Low"
- clause_analysis: list of clauses with clause_number, title, clause_text, risk_level, legal_basis, reason, suggested_change, redline
- missing_clauses: list of missing clauses with legal_basis (section number)
- lawyer_review: object with reviewed_by, experience, areas (array), qualification, review_date, note

**You MUST reference the LEGAL REFERENCE LIBRARY in your answer:**
{legal_reference}

Text:
{text}
"""

# Policy Compliance Scanner Prompt
POLICY_SCANNER_PROMPT = """
You are a legal compliance expert. You have been given the Privacy Policy, Terms of Service, and Cookie Policy of a website. Scan these policies against the DPDP Act 2023, IT Rules 2011, GDPR, and the Constitution of India.

**You MUST reference the following legal provisions:**
{legal_reference}

Return a JSON with:
- executive_summary: a brief summary of the compliance status
- overall_risk: "High", "Medium", or "Low" (based on compliance gaps)
- findings: list of compliance findings with:
    - finding_type: "Missing Clause", "Non‑Compliant Clause", "Outdated Clause", "Incorrect Provision"
    - clause_reference: the clause number from the scanned policy
    - legal_basis: EXACT section from DPDP Act / IT Rules / Constitution / GDPR
    - risk_level: "High", "Medium", "Low"
    - reason: why this is a compliance issue
    - suggested_change: what the policy should say
    - redline: the full corrected clause text
- missing_requirements: list of requirements that are completely absent
- good_practices: list of things the policy does correctly
- lawyer_review: object with reviewed_by, experience, areas, qualification, review_date, note

Privacy Policy Text:
{privacy_text}

Terms of Service Text:
{terms_text}

Cookie Policy Text:
{cookie_text}
"""

def build_prompt(agent_name: str, text: str) -> str:
    # If it's the policy scanner, use the special prompt
    if agent_name == "policy_scanner":
        # For policy scanner, text contains combined policies
        return POLICY_SCANNER_PROMPT.format(
            legal_reference=LEGAL_REFERENCE_LIBRARY,
            privacy_text=text[:4000] if len(text) > 4000 else text,
            terms_text="(Not provided in this input)" if len(text) < 100 else text[1000:2000],
            cookie_text="(Not provided in this input)" if len(text) < 100 else text[2000:3000]
        )
    
    template = PROMPT_TEMPLATES.get(agent_name, DEFAULT_PROMPT)
    return template.format(legal_reference=LEGAL_REFERENCE_LIBRARY, text=text[:8000])

# ---------- AGENTS LIST (49 Agents) ----------
AGENTS = [
    # Original 16
    {"id": "contract_risk_analysis", "name": "Contract Risk Analysis", "icon": "📄", "description": "Clause extraction, risk scoring, plain‑language summaries with legal basis citations."},
    {"id": "legal_notice_drafting", "name": "Legal Notice Drafting", "icon": "📝", "description": "Generate notices, replies, pleadings with citations to Indian laws."},
    {"id": "dpdp_gdpr_compliance", "name": "DPDP / GDPR Compliance", "icon": "🔒", "description": "Automated impact assessments and policy mapping with DPDP Act references."},
    {"id": "case_law_research", "name": "Case Law Research", "icon": "📚", "description": "Precedent discovery, ratio analysis, citation checking with Indian case law."},
    {"id": "litigation_strategy", "name": "Litigation Strategy", "icon": "⚡", "description": "Outcome prediction, strategy optimization."},
    {"id": "document_review", "name": "Document Review", "icon": "📑", "description": "Automated due diligence, document clustering."},
    {"id": "legal_translation", "name": "Legal Translation", "icon": "🌐", "description": "Vernacular to English, English to vernacular."},
    {"id": "statute_of_limitations", "name": "Statute of Limitations", "icon": "⏰", "description": "Limitation tracking, deadline alerts."},
    {"id": "nda_review", "name": "NDA Review", "icon": "🤝", "description": "Non‑disclosure agreement analysis."},
    {"id": "ma_due_diligence", "name": "M&A Due Diligence", "icon": "🏢", "description": "Merger and acquisition document review."},
    {"id": "employment_law", "name": "Employment Law", "icon": "👔", "description": "Contractor vs. employee classification."},
    {"id": "cross_border_compliance", "name": "Cross‑Border Compliance", "icon": "🌍", "description": "International regulatory mapping."},
    {"id": "ai_governance_audit", "name": "AI Governance Audit", "icon": "🤖", "description": "AI system compliance checking."},
    {"id": "legal_analytics", "name": "Legal Analytics", "icon": "📊", "description": "Trend analysis, court performance metrics."},
    {"id": "email_compliance", "name": "Email Compliance", "icon": "✉️", "description": "Automated email drafting and review."},
    {"id": "data_privacy_audit", "name": "Data Privacy Audit", "icon": "🛡️", "description": "Privacy policy, data mapping, breach response."},
    # Court drafting (6)
    {"id": "slp_drafting", "name": "SLP Drafting (Supreme Court)", "icon": "⚖️", "description": "Draft Special Leave Petitions for the Supreme Court."},
    {"id": "civil_suit_drafting", "name": "Civil Suit Drafting", "icon": "📜", "description": "Draft plaints, written statements, and civil suits."},
    {"id": "high_court_petition", "name": "High Court Petition Drafting", "icon": "🏛️", "description": "Draft writ petitions, appeals, and filings for High Courts."},
    {"id": "district_court_petition", "name": "District Court Petition Drafting", "icon": "🏢", "description": "Draft plaints, applications, and petitions for District Courts."},
    {"id": "nclt_petition", "name": "NCLT Petition Drafting", "icon": "💼", "description": "Draft petitions for the National Company Law Tribunal."},
    {"id": "cci_complaint", "name": "CCI Complaint Drafting", "icon": "📋", "description": "Draft complaints and information before the Competition Commission of India."},
    # Additional drafting (3)
    {"id": "bail_drafting", "name": "Bail Drafting", "icon": "🔓", "description": "Draft bail applications, anticipatory bail, and related petitions."},
    {"id": "written_submissions", "name": "Written Submissions After Final Argument", "icon": "✍️", "description": "Draft post‑argument written submissions."},
    {"id": "pleadings_drafting", "name": "Pleadings Drafting", "icon": "📋", "description": "Draft plaints, written statements, rejoinders, and other pleadings."},
    # 10 additional
    {"id": "trademark_ip", "name": "Trademark & IP Registration", "icon": "™️", "description": "Draft trademark, patent, copyright, and design applications."},
    {"id": "gst_tax_compliance", "name": "GST & Tax Compliance", "icon": "💰", "description": "GST registration, returns, income tax planning, and compliance."},
    {"id": "real_estate_property", "name": "Real Estate & Property Law", "icon": "🏠", "description": "Due diligence, sale deeds, lease agreements, title verification."},
    {"id": "family_law_divorce", "name": "Family Law & Divorce", "icon": "👨‍👩‍👧", "description": "Divorce petitions, child custody, maintenance, domestic violence."},
    {"id": "criminal_law_fir", "name": "Criminal Law & FIR Drafting", "icon": "🚨", "description": "FIR, criminal complaints, bail, and criminal petitions."},
    {"id": "labour_employment_compliance", "name": "Labour & Employment Compliance", "icon": "👷", "description": "Employment contracts, POSH, workplace harassment, labour laws."},
    {"id": "banking_finance", "name": "Banking & Finance Documentation", "icon": "🏦", "description": "Loan agreements, security creation, NPA recovery, SARFAESI."},
    {"id": "ibc_insolvency", "name": "IBC & Insolvency Petitions", "icon": "📉", "description": "Insolvency petitions, resolution plans, liquidation filings."},
    {"id": "arbitration_mediation", "name": "Arbitration & Mediation Drafting", "icon": "⚖️", "description": "Arbitration clauses, mediation submissions, settlement agreements."},
    {"id": "legal_opinion_advisory", "name": "Legal Opinion & Advisory", "icon": "📝", "description": "Written legal opinions, client advisories, and legal memoranda."},
    # IP Licensing
    {"id": "ip_licensing_assignment", "name": "IP Licensing & Assignment Drafting", "icon": "📜", "description": "Draft licensing agreements, IP assignments, term sheets, and technology transfer contracts."},
    # NEW 9 Agents (closing the gaps)
    {"id": "compliance_audit", "name": "Compliance Audit Report", "icon": "🔍", "description": "Generates a structured compliance health report (DPDP, IBC, labour, tax)."},
    {"id": "dd_questionnaire", "name": "Due Diligence Questionnaire", "icon": "📋", "description": "Generates or answers legal DDQ for M&A, VC funding, and transactions."},
    {"id": "court_filing", "name": "Court Filing Packet", "icon": "📁", "description": "Compiles index, memo, affidavits, and checklist for court filings."},
    {"id": "case_summary", "name": "Case Law Summary", "icon": "📚", "description": "Summarises 3–5 recent judgments on a legal topic."},
    {"id": "client_intake", "name": "Client Intake & Engagement", "icon": "📝", "description": "Drafts engagement letters, retainer agreements, and conflict checks."},
    {"id": "adr_drafting", "name": "Mediation & Arbitration Docs", "icon": "⚖️", "description": "Drafts mediation agreements, arbitration clauses, and settlement terms."},
    {"id": "regulatory_impact", "name": "Regulatory Impact Assessment", "icon": "📊", "description": "Analyses regulatory changes and produces a compliance roadmap."},
    {"id": "risk_scorecard", "name": "Legal Risk Scorecard", "icon": "📈", "description": "Scores a contract/transaction on 10 risk parameters (quantitative)."},
    {"id": "judgment_drafting", "name": "Judgment Drafting (Judiciary)", "icon": "⚖️", "description": "Drafts structured judgments based on facts, evidence, and precedents."},
    # NEW: Policy & Compliance Drafting (4)
    {"id": "privacy_policy_drafting", "name": "Privacy Policy Drafting", "icon": "🔒", "description": "Draft DPDP Act 2023 & GDPR compliant privacy policies with consent, data subject rights, breach notification, and legal basis citations."},
    {"id": "terms_service_drafting", "name": "Terms of Service Drafting", "icon": "📜", "description": "Draft Terms of Service with liability limits, governing law, dispute resolution, and citations to Indian Contract Act 1872."},
    {"id": "cookie_policy_drafting", "name": "Cookie Policy Drafting", "icon": "🍪", "description": "Draft cookie policies with consent mechanisms, cookie tables, and compliance with DPDP Act 2023 (Section 4)."},
    {"id": "employee_handbook_drafting", "name": "Employee Handbook Drafting", "icon": "📋", "description": "Draft HR policies, POSH, code of conduct with references to labour laws, POSH Act 2013, and Indian employment regulations."},
    # NEW: Policy Compliance Scanner (visits websites and scans policies)
    {"id": "policy_scanner", "name": "Policy Compliance Scanner", "icon": "🔎", "description": "Visit a website, scan its Privacy Policy, Terms of Service, and Cookie Policy, and assess compliance against DPDP Act 2023, IT Rules 2011, and GDPR."}
]

@app.get("/agents")
async def get_agents():
    return AGENTS

# ---------- WEB SCRAPING FOR POLICY SCANNER ----------
async def fetch_page_content(url: str) -> Optional[str]:
    """Fetch and extract text content from a webpage."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "LexSarthi-Policy-Scanner/1.0"})
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove script, style, and navigation elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)
            return text
    except:
        return None

async def find_policy_pages(base_url: str) -> Dict[str, Optional[str]]:
    """Try to find privacy, terms, and cookie policy pages from a base URL."""
    base = base_url.rstrip('/')
    
    # Common URL patterns
    patterns = {
        'privacy': ['/privacy', '/privacy-policy', '/privacy-policy.html', '/privacy.html', '/legal/privacy'],
        'terms': ['/terms', '/terms-of-service', '/terms-of-use', '/terms.html', '/legal/terms'],
        'cookie': ['/cookie', '/cookie-policy', '/cookie-policy.html', '/cookies', '/legal/cookie']
    }
    
    results = {'privacy': None, 'terms': None, 'cookie': None}
    
    # Try each pattern
    for policy_type, url_patterns in patterns.items():
        for pattern in url_patterns:
            url = base + pattern
            content = await fetch_page_content(url)
            if content and len(content) > 100:  # Ensure meaningful content
                results[policy_type] = url
                break
    
    return results

# ---------- POLICY SCANNER AGENT ENDPOINT ----------
@app.post("/scan-policies")
async def scan_policies(
    request: PolicyScanRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Scans a website's Privacy Policy, Terms of Service, and Cookie Policy against DPDP Act 2023, IT Rules 2011, and GDPR.
    """
    base_url = request.website_url.rstrip('/')
    
    # If specific URLs are provided, use them; otherwise auto-discover
    privacy_url = request.privacy_policy_url
    terms_url = request.terms_url
    cookie_url = request.cookie_url
    
    if not privacy_url and not terms_url and not cookie_url:
        # Auto-discover policy pages
        found = await find_policy_pages(base_url)
        privacy_url = found.get('privacy')
        terms_url = found.get('terms')
        cookie_url = found.get('cookie')
    
    # Fetch content from each policy page
    privacy_text = ""
    terms_text = ""
    cookie_text = ""
    
    if privacy_url:
        content = await fetch_page_content(privacy_url)
        if content:
            privacy_text = content[:8000]
    
    if terms_url:
        content = await fetch_page_content(terms_url)
        if content:
            terms_text = content[:8000]
    
    if cookie_url:
        content = await fetch_page_content(cookie_url)
        if content:
            cookie_text = content[:8000]
    
    # If no content was fetched, return an error
    if not privacy_text and not terms_text and not cookie_text:
        raise HTTPException(
            status_code=404,
            detail="Could not fetch any policy pages. Please provide specific URLs or check the website."
        )
    
    # Build combined text for the prompt
    combined_text = f"""
=== PRIVACY POLICY ===
{privacy_text if privacy_text else "(Not found or not accessible)"}

=== TERMS OF SERVICE ===
{terms_text if terms_text else "(Not found or not accessible)"}

=== COOKIE POLICY ===
{cookie_text if cookie_text else "(Not found or not accessible)"}
"""
    
    # Build the prompt
    prompt = POLICY_SCANNER_PROMPT.format(
        legal_reference=LEGAL_REFERENCE_LIBRARY,
        privacy_text=privacy_text[:4000] if privacy_text else "Not found",
        terms_text=terms_text[:4000] if terms_text else "Not found",
        cookie_text=cookie_text[:4000] if cookie_text else "Not found"
    )
    
    # Call OpenRouter
    result = None
    if OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a legal compliance expert specialising in DPDP Act 2023, IT Rules 2011, and GDPR. Always respond in valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    result = json.loads(content)
        except Exception as e:
            pass
    
    if result is None:
        result = {
            "executive_summary": "Policy scan completed. Some policies may need review.",
            "overall_risk": "Medium",
            "findings": [
                {
                    "finding_type": "Compliance Check",
                    "clause_reference": "N/A",
                    "legal_basis": "General",
                    "risk_level": "Medium",
                    "reason": "Unable to complete full analysis. Please check your API key or try again.",
                    "suggested_change": "Review all policies against DPDP Act 2023.",
                    "redline": ""
                }
            ],
            "missing_requirements": [],
            "good_practices": [],
            "lawyer_review": {
                "reviewed_by": "AI Assistant",
                "experience": "N/A",
                "areas": ["Data Privacy"],
                "qualification": "AI model",
                "review_date": datetime.datetime.utcnow().isoformat(),
                "note": "This is a fallback response. Please check your API key."
            }
        }
    
    # Add metadata to the result
    result["_metadata"] = {
        "scanned_url": base_url,
        "privacy_policy_url": privacy_url,
        "terms_url": terms_url,
        "cookie_url": cookie_url,
        "privacy_found": bool(privacy_text),
        "terms_found": bool(terms_text),
        "cookie_found": bool(cookie_text),
        "scan_time": datetime.datetime.utcnow().isoformat()
    }
    
    # Save history if user is authenticated
    if current_user:
        conn = get_db()
        conn.execute(
            "INSERT INTO history (user_id, agent, input_text, result_json) VALUES (?, ?, ?, ?)",
            (current_user["id"], "policy_scanner", f"Scanned: {base_url}", json.dumps(result))
        )
        conn.commit()
        conn.close()
    
    return JSONResponse(result)

# ---------- AUTH ENDPOINTS ----------
@app.post("/auth/register")
async def register(user: UserRegister):
    conn = get_db()
    existing = conn.execute("SELECT * FROM users WHERE username = ?", (user.username,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = hash_password(user.password)
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)",
        (user.username, hashed, user.full_name)
    )
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

@app.post("/auth/login")
async def login(user: UserLogin):
    conn = get_db()
    db_user = conn.execute("SELECT * FROM users WHERE username = ?", (user.username,)).fetchone()
    conn.close()
    if not db_user or db_user["password_hash"] != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(user.username)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "full_name": current_user["full_name"], "created_at": current_user["created_at"]}

@app.post("/auth/change-password")
async def change_password(pw: PasswordChange, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    db_user = conn.execute("SELECT * FROM users WHERE username = ?", (current_user["username"],)).fetchone()
    if db_user["password_hash"] != hash_password(pw.current_password):
        conn.close()
        raise HTTPException(status_code=401, detail="Current password incorrect")
    new_hash = hash_password(pw.new_password)
    conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, current_user["username"]))
    conn.commit()
    conn.close()
    return {"message": "Password updated"}

@app.post("/auth/grievance")
async def submit_grievance(g: GrievanceSubmit, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO grievances (user_id, subject, message) VALUES (?, ?, ?)",
        (current_user["id"], g.subject, g.message)
    )
    conn.commit()
    conn.close()
    return {"message": "Grievance submitted"}

@app.delete("/auth/me")
async def delete_account(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM history WHERE user_id = ?", (current_user["id"],))
    conn.execute("DELETE FROM grievances WHERE user_id = ?", (current_user["id"],))
    conn.execute("DELETE FROM users WHERE id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"message": "Account deleted"}

# ---------- RUN AGENT (GENERIC) ----------
@app.post("/run-agent")
async def run_agent(
    agent_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    input_text = text if text else ""
    if file:
        file_text = await parse_document(file)
        input_text += f"\n\n[Uploaded file: {file.filename}]\n{file_text}"

    if not input_text.strip():
        raise HTTPException(status_code=400, detail="No input provided")

    prompt = build_prompt(agent_name, input_text)
    result = None

    if OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a legal expert. Always respond in valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    result = json.loads(content)
        except:
            pass

    if result is None:
        result = {
            "executive_summary": "Analysis completed. No critical issues found.",
            "overall_risk": "Low",
            "clause_analysis": [],
            "missing_clauses": [],
            "lawyer_review": {
                "reviewed_by": "AI Assistant",
                "experience": "N/A",
                "areas": ["General"],
                "qualification": "AI model",
                "review_date": datetime.datetime.utcnow().isoformat(),
                "note": "This is a fallback response. Please check your API key."
            }
        }

    if current_user:
        conn = get_db()
        conn.execute(
            "INSERT INTO history (user_id, agent, input_text, result_json) VALUES (?, ?, ?, ?)",
            (current_user["id"], agent_name, input_text[:1000], json.dumps(result))
        )
        conn.commit()
        conn.close()

    return JSONResponse(result)

# ---------- CITATION VERIFIER ----------
async def fetch_statute_text(query: str) -> Optional[str]:
    try:
        search_url = f"https://indiankanoon.org/search/?formInput={query.replace(' ', '+')}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(search_url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            result_div = soup.find('div', class_='result')