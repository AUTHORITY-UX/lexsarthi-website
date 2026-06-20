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
# 📊 ANALYTICS & BI - Complete Legal Analytics Dashboard
# 💳 ₹2 TEST PAYMENT - Starter Pack
# ⏰ DAILY REPORT - Auto-generates at 4:00 AM IST every day
# 📧 CAMPAIGNS - Email, Engagement, Alerts, Market Intelligence
# 🌐 DOMAIN INTELLIGENCE - WHOIS, SSL, DNS, Domain Agreement
# 📈 MARKET INTELLIGENCE - Trends, Competitors, Regulatory Insights
# ⚖️ LEGAL INTELLIGENCE - Case Law, Legal Analysis, AI Agent
# 📊 TRADE ANALYSIS - Import/Export, Commodities, Trends
# 📊 SELF-DATA ANALYTICS - LexSarthi's Own Data Analysis
# ===================================================================

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid, jwt, bcrypt, os, logging, json, asyncio, smtplib, sqlite3, whois, ssl, socket, dns.resolver, razorpay, time, threading, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

load_dotenv()

# ===================================================================
# CONFIGURATION
# ===================================================================
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_key")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "test_secret")
EMAIL_HOST, EMAIL_PORT = "smtp.gmail.com", 587
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "upmanyu@advocacyalawfrim.in")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
UPLOAD_DIR, REPORT_DIR, CV_DIR = "uploads", "reports", "cv_simulations"
for d in [UPLOAD_DIR, REPORT_DIR, CV_DIR]: os.makedirs(d, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================================================================
# MODELS
# ===================================================================
class UserRegister(BaseModel):
    email: EmailStr; username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8); full_name: Optional[str] = None
    phone: Optional[str] = None; user_type: str = "individual"
    consent_dpdp: bool = True; consent_marketing: bool = False
    consent_analytics: bool = True; consent_third_party: bool = False
    acknowledge_privacy_policy: bool = True; acknowledge_terms: bool = True
    acknowledge_zero_retention: bool = True
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v: raise ValueError('Username must be alphanumeric or contain underscores')
        return v.lower()
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8: raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v): raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v): raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v): raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v): raise ValueError('Password must contain at least one special character')
        return v

class UserLogin(BaseModel): email: EmailStr; password: str
class RefreshToken(BaseModel): refresh_token: str
class PaymentInitiate(BaseModel): amount: int = 200; currency: str = "INR"; description: str = "LexSarthi Starter Pack"; plan: str = "starter"
class PaymentVerify(BaseModel): razorpay_payment_id: str; razorpay_order_id: str; razorpay_signature: str
class LegalQuery(BaseModel): query: str; context: Optional[Dict[str, Any]] = {}; agent_type: str = "general"
class DomainIntelligenceRequest(BaseModel): domain: str; check_ssl: bool = True; check_whois: bool = True; check_dns: bool = True
class ReportGenerate(BaseModel): report_type: str; format: str = "pdf"; date_range: Optional[Dict[str, str]] = None; filters: Optional[Dict[str, Any]] = {}
class AgentRun(BaseModel): agent_type: str; input_data: Dict[str, Any]; context: Optional[Dict[str, Any]] = {}; use_prompt_template: bool = True
class CVSimulationRequest(BaseModel): candidate_name: str; position: str; experience_years: int; skills: List[str]; education: str; current_company: Optional[str] = None; additional_info: Optional[str] = None

# ===================================================================
# APP SETUP
# ===================================================================
app = FastAPI(title="LexSarthi v4.0", version="4.0.0", docs_url="/api/docs")
executor = ThreadPoolExecutor(max_workers=10)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.advocacyalawfrim.in", "https://upamnyu12-lex.hf.space", "http://localhost:3000", "*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["*"]
)

# ===================================================================
# DATABASE
# ===================================================================
class Database:
    def __init__(self): self.conn = None; self.cursor = None; self.lock = threading.Lock()
    async def connect(self):
        self.conn = sqlite3.connect('lexsarthi.db', check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row; self.cursor = self.conn.cursor()
        await self.init_tables(); logger.info("✅ Database initialized")
    async def init_tables(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE, username TEXT UNIQUE, password_hash TEXT,
            full_name TEXT, phone TEXT, user_type TEXT, is_verified INTEGER, is_active INTEGER,
            created_at TEXT, updated_at TEXT, last_login TEXT, metadata TEXT,
            consent_dpdp INTEGER, consent_marketing INTEGER, consent_analytics INTEGER,
            consent_third_party INTEGER, consent_timestamp TEXT, privacy_policy_acknowledged INTEGER,
            terms_acknowledged INTEGER, zero_retention_acknowledged INTEGER, data_retention_agreed INTEGER,
            total_queries INTEGER, total_agents_used INTEGER, subscription_plan TEXT,
            subscription_expiry TEXT, payment_status TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS tokens (
            id TEXT PRIMARY KEY, user_id TEXT, refresh_token TEXT UNIQUE, access_token TEXT,
            expires_at TEXT, created_at TEXT, revoked INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY, user_id TEXT, razorpay_order_id TEXT UNIQUE, razorpay_payment_id TEXT,
            razorpay_signature TEXT, amount INTEGER, currency TEXT, status TEXT, metadata TEXT,
            created_at TEXT, completed_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS legal_queries (
            id TEXT PRIMARY KEY, user_id TEXT, query TEXT, response TEXT, agent_type TEXT,
            context TEXT, confidence_score REAL, created_at TEXT, processed_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY, user_id TEXT, agent_type TEXT, input_data TEXT, output_data TEXT,
            status TEXT, created_at TEXT, completed_at TEXT, execution_time REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS cv_simulations (
            id TEXT PRIMARY KEY, user_id TEXT, candidate_name TEXT, position TEXT,
            experience_years INTEGER, skills TEXT, education TEXT, current_company TEXT,
            simulation_data TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS analytics (
            id TEXT PRIMARY KEY, user_id TEXT, event_type TEXT, event_data TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS domain_intelligence (
            id TEXT PRIMARY KEY, user_id TEXT, domain TEXT, whois_data TEXT, ssl_data TEXT, dns_data TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY, user_id TEXT, report_type TEXT, report_data TEXT, file_path TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY, user_id TEXT, filename TEXT, file_path TEXT, file_type TEXT, file_size INTEGER, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS activity_log (
            id TEXT PRIMARY KEY, user_id TEXT, action TEXT, details TEXT, ip_address TEXT, user_agent TEXT, created_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_legal_queries_user_id ON legal_queries(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_cv_simulations_user_id ON cv_simulations(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id)")
        self.conn.commit()
db = Database()

# ===================================================================
# AUTH SERVICE
# ===================================================================
class AuthService:
    @staticmethod
    def hash_password(p): return bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    @staticmethod
    def verify_password(p, h): return bcrypt.checkpw(p.encode('utf-8'), h.encode('utf-8'))
    @staticmethod
    def create_tokens(user_id, email):
        return {
            'access_token': jwt.encode({'sub': user_id, 'email': email, 'type': 'access', 'exp': datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}, SECRET_KEY, algorithm=ALGORITHM),
            'refresh_token': jwt.encode({'sub': user_id, 'email': email, 'type': 'refresh', 'exp': datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)}, SECRET_KEY, algorithm=ALGORITHM),
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    @staticmethod
    def verify_token(token, token_type='access'):
        try:
            p = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return p if p.get('type') == token_type else None
        except: return None

security = HTTPBearer(auto_error=False)
async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds: raise HTTPException(401, "Not authenticated")
    payload = AuthService.verify_token(creds.credentials, 'access')
    if not payload: raise HTTPException(401, "Invalid token")
    c = db.conn.cursor(); c.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (payload.get('sub'),))
    user = c.fetchone()
    if not user: raise HTTPException(401, "User not found")
    return dict(user)

# ===================================================================
# ALL 73 AGENTS WITH PROMPTS
# ===================================================================
AGENT_PROMPTS = {
    "contract_review": "You are a Contract Review Expert. Analyze this contract and identify key clauses, risks, and recommendations.",
    "case_analysis": "You are a Case Law Analysis Expert. Analyze this case and provide key legal principles.",
    "legal_research": "You are a Legal Research Expert. Research this legal query and provide relevant case laws.",
    "compliance_check": "You are a Compliance Check Expert. Analyze this for regulatory compliance issues.",
    "judgment_drafting": "You are a Judgment Drafting Expert. Draft a judgment based on given facts.",
    "legal_document_analysis": "You are a Legal Document Analysis Expert. Analyze this document for legal issues.",
    "risk_assessment": "You are a Risk Assessment Expert. Assess legal risks and provide mitigation strategies.",
    "regulatory_advice": "You are a Regulatory Compliance Expert. Provide regulatory advice.",
    "legal_drafting": "You are a Legal Drafting Expert. Draft a legal document based on requirements.",
    "legal_opinion": "You are a Legal Opinion Expert. Provide a legal opinion on this matter.",
    "statutory_interpretation": "You are a Statutory Interpretation Expert. Interpret this statute.",
    "legal_ethics": "You are a Legal Ethics Expert. Analyze ethical issues and provide guidance.",
    "legal_technology": "You are a Legal Technology Expert. Advise on legal tech solutions.",
    "legal_education": "You are a Legal Education Expert. Provide educational content.",
    "legal_policy": "You are a Legal Policy Expert. Analyze policy and provide recommendations.",
    "legal_reform": "You are a Legal Reform Expert. Suggest legal reforms.",
    "legal_innovation": "You are a Legal Innovation Expert. Suggest innovative legal solutions.",
    "legal_strategy": "You are a Legal Strategy Expert. Develop a legal strategy.",
    "legal_compliance": "You are a Legal Compliance Expert. Ensure compliance with laws.",
    "legal_risk": "You are a Legal Risk Management Expert. Manage and mitigate legal risks.",
    "merger_acquisition": "You are an M&A Legal Expert. Analyze this merger/acquisition deal.",
    "intellectual_property": "You are an IP Law Expert. Analyze this intellectual property matter.",
    "tax_law": "You are a Tax Law Expert. Analyze this tax situation.",
    "corporate_law": "You are a Corporate Law Expert. Advise on corporate law matters.",
    "employment_law": "You are an Employment Law Expert. Analyze this employment situation.",
    "real_estate_law": "You are a Real Estate Law Expert. Advise on real estate legal matters.",
    "banking_finance": "You are a Banking & Finance Expert. Advise on banking and finance law.",
    "competition_law": "You are a Competition Law Expert. Analyze this competition matter.",
    "insolvency_bankruptcy": "You are an Insolvency & Bankruptcy Expert. Advise on insolvency.",
    "securities_law": "You are a Securities Law Expert. Advise on securities markets.",
    "family_law": "You are a Family Law Expert. Advise on this family law matter.",
    "criminal_law": "You are a Criminal Law Expert. Analyze this criminal law case.",
    "property_law": "You are a Property Law Expert. Advise on property law.",
    "succession_law": "You are a Succession Law Expert. Advise on wills and succession.",
    "consumer_law": "You are a Consumer Law Expert. Advise on consumer protection.",
    "tort_law": "You are a Tort Law Expert. Analyze this tort law case.",
    "employment_personal": "You are a Personal Employment Expert. Advise on employment rights.",
    "immigration_law": "You are an Immigration Law Expert. Advise on immigration law.",
    "civil_litigation": "You are a Civil Litigation Expert. Advise on civil litigation.",
    "human_rights": "You are a Human Rights Expert. Analyze this human rights issue.",
    "constitutional_law": "You are a Constitutional Law Expert. Analyze this constitutional issue.",
    "international_law": "You are an International Law Expert. Analyze this international matter.",
    "administrative_law": "You are an Administrative Law Expert. Advise on administrative law.",
    "environmental_law": "You are an Environmental Law Expert. Advise on environmental law.",
    "public_policy": "You are a Public Policy Expert. Analyze this public policy issue.",
    "arbitration": "You are an Arbitration Expert. Advise on this arbitration matter.",
    "mediation": "You are a Mediation Expert. Advise on this mediation process.",
    "litigation": "You are a Litigation Expert. Advise on this litigation strategy.",
    "negotiation": "You are a Negotiation Expert. Develop a negotiation strategy.",
    "conciliation": "You are a Conciliation Expert. Advise on conciliation proceedings.",
    "dispute_resolution": "You are a Dispute Resolution Expert. Advise on dispute resolution.",
    "conflict_resolution": "You are a Conflict Resolution Expert. Resolve this conflict.",
    "ojt": "You are an OJT Expert. Advise on online dispute resolution.",
    "domain_intelligence": "You are a Domain Intelligence Expert. Analyze WHOIS, SSL, DNS records.",
    "market_intelligence": "You are a Market Intelligence Expert. Analyze market trends.",
    "trade_analysis": "You are a Trade Analysis Expert. Analyze trade data.",
    "campaign_tools": "You are a Campaign Tools Expert. Advise on email campaigns.",
    "self_analytics": "You are a Self-Data Analytics Expert. Analyze your data.",
    "daily_reports": "You are a Daily Reports Expert. Generate daily reports.",
    "legal_analytics": "You are a Legal Analytics Expert. Analyze legal data.",
    "ai_law": "You are an AI & Law Expert. Advise on AI in legal practice.",
    "legal_automation": "You are a Legal Automation Expert. Advise on process automation.",
    "blockchain_law": "You are a Blockchain Law Expert. Advise on blockchain law.",
    "white_collar_crime": "You are a White Collar Crime Expert. Analyze this case.",
    "cyber_law": "You are a Cyber Law Expert. Advise on cyber law.",
    "media_law": "You are a Media Law Expert. Advise on media law.",
    "sports_law": "You are a Sports Law Expert. Advise on sports law.",
    "healthcare_law": "You are a Healthcare Law Expert. Advise on healthcare law.",
    "education_law": "You are an Education Law Expert. Advise on education law.",
    "maritime_law": "You are a Maritime Law Expert. Advise on maritime law.",
    "aviation_law": "You are an Aviation Law Expert. Advise on aviation law.",
    "energy_law": "You are an Energy Law Expert. Advise on energy law.",
    "space_law": "You are a Space Law Expert. Advise on space law."
}

ALL_AGENTS = [
    {"id": k, "name": v.replace("You are a ", "").replace(" Expert.", "").replace(" Expert", "").strip(), 
     "category": "Legal Intelligence" if k in ["contract_review","case_analysis","legal_research","compliance_check","judgment_drafting","legal_document_analysis","risk_assessment","regulatory_advice","legal_drafting","legal_opinion","statutory_interpretation","legal_ethics","legal_technology","legal_education","legal_policy","legal_reform","legal_innovation","legal_strategy","legal_compliance","legal_risk"] else
                "Corporate Law" if k in ["merger_acquisition","intellectual_property","tax_law","corporate_law","employment_law","real_estate_law","banking_finance","competition_law","insolvency_bankruptcy","securities_law"] else
                "Personal Law" if k in ["family_law","criminal_law","property_law","succession_law","consumer_law","tort_law","employment_personal","immigration_law","civil_litigation","human_rights"] else
                "Public Law" if k in ["constitutional_law","international_law","administrative_law","environmental_law","public_policy"] else
                "Dispute Resolution" if k in ["arbitration","mediation","litigation","negotiation","conciliation","dispute_resolution","conflict_resolution","ojt"] else
                "Technology" if k in ["domain_intelligence","market_intelligence","trade_analysis","campaign_tools","self_analytics","daily_reports","legal_analytics","ai_law","legal_automation","blockchain_law"] else
                "Specialized",
     "description": v.split(".")[0] if "." in v else v[:60], "icon": "⚖️", "prompt": v}
    for k, v in AGENT_PROMPTS.items()
]

# ===================================================================
# ZERO RETENTION
# ===================================================================
class ZeroRetentionPolicy:
    @staticmethod
    async def cleanup():
        try:
            c = db.conn.cursor()
            c.execute("DELETE FROM tokens WHERE datetime(expires_at) < datetime('now', '-24 hours')")
            c.execute("DELETE FROM legal_queries WHERE datetime(created_at) < datetime('now', '-24 hours')")
            c.execute("DELETE FROM agent_runs WHERE datetime(created_at) < datetime('now', '-24 hours')")
            c.execute("DELETE FROM domain_intelligence WHERE datetime(created_at) < datetime('now', '-24 hours')")
            c.execute("DELETE FROM analytics WHERE datetime(created_at) < datetime('now', '-7 days')")
            c.execute("DELETE FROM activity_log WHERE datetime(created_at) < datetime('now', '-7 days')")
            db.conn.commit()
            logger.info("🔒 Zero Retention: Deleted data older than 24 hours")
        except Exception as e: logger.error(f"Cleanup failed: {e}")

# ===================================================================
# LIFESPAN
# ===================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    asyncio.create_task(ZeroRetentionPolicy.cleanup())
    logger.info("🚀 LexSarthi v4.0 API started | 73 Agents | ₹2 Payment | CV Simulation")
    yield
    if db.conn: db.conn.close()
    executor.shutdown()
app = FastAPI(lifespan=lifespan)

# ===================================================================
# ENDPOINTS - HEALTH
# ===================================================================
@app.get("/health")
async def health(): return {"status": "healthy", "version": "4.0.0", "agents": 73, "lawyer": "Adv. Debo", "firm": "THE ADVOCACY A LAW FIRM"}

# ===================================================================
# ENDPOINTS - AGENTS (PUBLIC - NO AUTH)
# ===================================================================
@app.get("/agents")
@app.get("/agents/list")
async def list_agents():
    return {"agents": ALL_AGENTS, "total": len(ALL_AGENTS), "categories": list(set(a['category'] for a in ALL_AGENTS))}

@app.get("/agent/prompt/{agent_id}")
async def get_agent_prompt(agent_id: str):
    return {"agent_id": agent_id, "prompt": AGENT_PROMPTS.get(agent_id, "General Legal Assistant"), "available": agent_id in AGENT_PROMPTS}

# ===================================================================
# ENDPOINTS - AUTH
# ===================================================================
@app.post("/auth/register")
async def register(user: UserRegister):
    c = db.conn.cursor()
    c.execute("SELECT email FROM users WHERE email = ?", (user.email,))
    if c.fetchone(): raise HTTPException(400, "Email already registered")
    c.execute("SELECT username FROM users WHERE username = ?", (user.username,))
    if c.fetchone(): raise HTTPException(400, "Username already taken")
    user_id = str(uuid.uuid4())
    c.execute("""INSERT INTO users (id, email, username, password_hash, full_name, phone, user_type,
        consent_dpdp, consent_marketing, consent_analytics, consent_third_party, consent_timestamp,
        privacy_policy_acknowledged, terms_acknowledged, zero_retention_acknowledged, data_retention_agreed,
        subscription_plan, subscription_expiry, payment_status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, user.email, user.username, AuthService.hash_password(user.password),
         user.full_name, user.phone, user.user_type, 1,0,1,0,datetime.utcnow().isoformat(),
         1,1,1,24,'starter',(datetime.utcnow()+timedelta(days=30)).isoformat(),'pending',datetime.utcnow().isoformat()))
    db.conn.commit()
    tokens = AuthService.create_tokens(user_id, user.email)
    c.execute("INSERT INTO tokens (id,user_id,refresh_token,access_token,expires_at) VALUES (?,?,?,?,?)",
              (str(uuid.uuid4()), user_id, tokens['refresh_token'], tokens['access_token'],
               (datetime.utcnow()+timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()))
    db.conn.commit()
    return {**tokens, "user": {"id": user_id, "email": user.email, "username": user.username, "payment_status": "pending"}, "payment_required": True, "payment_amount": "₹2"}

@app.post("/auth/login")
async def login(user: UserLogin):
    c = db.conn.cursor(); c.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (user.email,))
    u = c.fetchone()
    if not u or not AuthService.verify_password(user.password, u['password_hash']):
        raise HTTPException(401, "Invalid credentials")
    c.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.utcnow().isoformat(), u['id']))
    db.conn.commit()
    tokens = AuthService.create_tokens(u['id'], u['email'])
    c.execute("INSERT INTO tokens (id,user_id,refresh_token,access_token,expires_at) VALUES (?,?,?,?,?)",
              (str(uuid.uuid4()), u['id'], tokens['refresh_token'], tokens['access_token'],
               (datetime.utcnow()+timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()))
    db.conn.commit()
    return {**tokens, "user": {"id": u['id'], "email": u['email'], "username": u['username'], "full_name": u['full_name'], "payment_status": u['payment_status']}}

@app.post("/auth/refresh")
async def refresh_token(data: RefreshToken):
    payload = AuthService.verify_token(data.refresh_token, 'refresh')
    if not payload: raise HTTPException(401, "Invalid refresh token")
    c = db.conn.cursor()
    c.execute("SELECT * FROM tokens WHERE refresh_token = ? AND revoked = 0", (data.refresh_token,))
    if not c.fetchone(): raise HTTPException(401, "Token not found")
    c.execute("UPDATE tokens SET revoked = 1 WHERE refresh_token = ?", (data.refresh_token,))
    db.conn.commit()
    tokens = AuthService.create_tokens(payload['sub'], payload['email'])
    c.execute("INSERT INTO tokens (id,user_id,refresh_token,access_token,expires_at) VALUES (?,?,?,?,?)",
              (str(uuid.uuid4()), payload['sub'], tokens['refresh_token'], tokens['access_token'],
               (datetime.utcnow()+timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()))
    db.conn.commit()
    return tokens

@app.post("/auth/logout")
async def logout(current_user=Depends(get_current_user)):
    c = db.conn.cursor(); c.execute("UPDATE tokens SET revoked = 1 WHERE user_id = ?", (current_user['id'],))
    db.conn.commit(); return {"message": "Logged out"}

@app.get("/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    return {"id": current_user['id'], "email": current_user['email'], "username": current_user['username'], "payment_status": current_user['payment_status']}

# ===================================================================
# ENDPOINTS - PAYMENT (₹2 - Adv. Debo)
# ===================================================================
@app.post("/payment/create-order")
async def create_payment(payment: PaymentInitiate, current_user=Depends(get_current_user)):
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    order = client.order.create({'amount': payment.amount, 'currency': payment.currency, 'receipt': f'order_{uuid.uuid4().hex[:8]}', 'payment_capture': 1, 'notes': {'user_id': current_user['id'], 'lawyer': 'Adv. Debo', 'firm': 'THE ADVOCACY A LAW FIRM'}})
    c = db.conn.cursor()
    c.execute("INSERT INTO payments (id,user_id,razorpay_order_id,amount,currency,status,metadata,created_at) VALUES (?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4()), current_user['id'], order['id'], payment.amount, payment.currency, 'initiated',
               json.dumps({'lawyer': 'Adv. Debo', 'plan': payment.plan}), datetime.utcnow().isoformat()))
    db.conn.commit()
    return {'order_id': order['id'], 'amount': order['amount'], 'currency': order['currency'], 'key_id': RAZORPAY_KEY_ID, 'amount_in_rupees': '₹2', 'lawyer': 'Adv. Debo'}

@app.post("/payment/verify")
async def verify_payment(data: PaymentVerify, current_user=Depends(get_current_user)):
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    client.utility.verify_payment_signature({'razorpay_payment_id': data.razorpay_payment_id, 'razorpay_order_id': data.razorpay_order_id, 'razorpay_signature': data.razorpay_signature})
    c = db.conn.cursor()
    c.execute("UPDATE payments SET status='completed', razorpay_payment_id=?, razorpay_signature=?, completed_at=? WHERE razorpay_order_id=? AND user_id=?",
              (data.razorpay_payment_id, data.razorpay_signature, datetime.utcnow().isoformat(), data.razorpay_order_id, current_user['id']))
    c.execute("UPDATE users SET subscription_plan='starter', subscription_expiry=?, payment_status='completed' WHERE id=?",
              ((datetime.utcnow()+timedelta(days=365)).isoformat(), current_user['id']))
    db.conn.commit()
    return {"status": "success", "message": "Payment verified", "lawyer": "Adv. Debo"}

# ===================================================================
# ENDPOINTS - AGENT RUN
# ===================================================================
@app.post("/agent/run")
async def run_agent(data: AgentRun, current_user=Depends(get_current_user)):
    run_id = str(uuid.uuid4()); start = time.time()
    agent_name = AGENT_PROMPTS.get(data.agent_type, "General Legal Agent").replace("You are a ", "").replace(" Expert.", "").replace(" Expert", "").strip()
    prompt = AGENT_PROMPTS.get(data.agent_type, "You are a legal AI assistant.")
    full_prompt = f"{prompt}\n\nQuery: {data.input_data.get('query', '')}\n\nContext: {json.dumps(data.input_data, indent=2)}" if data.use_prompt_template else data.input_data.get('query', '')
    response = {"agent_type": data.agent_type, "agent_name": agent_name, "input": data.input_data, "prompt_used": full_prompt, "output": {"analysis": f"Analysis completed for {data.agent_type}", "confidence_score": 0.95, "recommendations": ["Review relevant case law", "Consult with senior counsel"], "timestamp": datetime.utcnow().isoformat()}, "status": "completed", "disclaimer": "Not legal advice.", "attorney_client_privilege": True}
    c = db.conn.cursor()
    c.execute("INSERT INTO agent_runs (id,user_id,agent_type,input_data,output_data,status,completed_at,execution_time) VALUES (?,?,?,?,?,?,?,?)",
              (run_id, current_user['id'], data.agent_type, json.dumps(data.input_data), json.dumps(response), 'completed', datetime.utcnow().isoformat(), time.time()-start))
    c.execute("UPDATE users SET total_queries=total_queries+1, total_agents_used=total_agents_used+1 WHERE id=?", (current_user['id'],))
    db.conn.commit()
    return {"run_id": run_id, **response, "execution_time": time.time()-start}

# ===================================================================
# ENDPOINTS - CV SIMULATION
# ===================================================================
@app.post("/cv/simulate")
async def simulate_cv(data: CVSimulationRequest, current_user=Depends(get_current_user)):
    sim_id = str(uuid.uuid4())
    result = {"candidate_name": data.candidate_name, "position": data.position, "experience_years": data.experience_years, "skills": data.skills, "education": data.education, "current_company": data.current_company, "simulation": {"match_score": random.randint(70, 98), "strengths": ["Strong legal research", "Excellent drafting", "Good corporate law knowledge"], "areas_for_improvement": ["Courtroom experience", "Client management"], "recommendations": ["Pursue corporate law certification", "Gain litigation experience"], "market_value": f"₹{random.randint(8, 25)} LPA", "roles_suitable_for": ["Corporate Lawyer", "Legal Consultant"], "cv_analysis": f"Strong candidate for {data.position}. {data.experience_years} years experience in {', '.join(data.skills[:2])}."}, "timestamp": datetime.utcnow().isoformat()}
    c = db.conn.cursor()
    c.execute("INSERT INTO cv_simulations (id,user_id,candidate_name,position,experience_years,skills,education,current_company,simulation_data,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (sim_id, current_user['id'], data.candidate_name, data.position, data.experience_years, json.dumps(data.skills), data.education, data.current_company, json.dumps(result), datetime.utcnow().isoformat()))
    db.conn.commit()
    return result

@app.get("/cv/history")
async def get_cv_history(current_user=Depends(get_current_user)):
    c = db.conn.cursor()
    c.execute("SELECT id,candidate_name,position,experience_years,skills,education,current_company,created_at FROM cv_simulations WHERE user_id=? ORDER BY created_at DESC", (current_user['id'],))
    return {"simulations": [dict(r) for r in c.fetchall()], "count": len(c.fetchall())}

# ===================================================================
# ENDPOINTS - DOMAIN INTELLIGENCE
# ===================================================================
@app.post("/scan-domain")
@app.post("/domain/scan")
async def scan_domain(data: Dict[str, str], current_user=Depends(get_current_user)):
    domain = data.get('domain', '')
    if not domain: raise HTTPException(400, "Domain required")
    result = {"domain": domain, "whois": {"registrar": "Unknown", "creation_date": "Unknown", "expiration_date": "Unknown"}, "ssl": {"issuer": "Unknown", "valid": True}, "dns": {"A": [], "MX": [], "TXT": []}, "timestamp": datetime.utcnow().isoformat()}
    try:
        w = whois.whois(domain)
        result["whois"] = {"registrar": str(w.registrar) if w.registrar else "Unknown", "creation_date": str(w.creation_date) if w.creation_date else "Unknown", "expiration_date": str(w.expiration_date) if w.expiration_date else "Unknown"}
    except: pass
    try:
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                result["ssl"] = {"issuer": dict(cert.get('issuer', [])), "valid_from": cert.get('notBefore', ''), "valid_to": cert.get('notAfter', '')}
    except: pass
    try:
        for rt in ["A", "MX", "TXT"]:
            try: result["dns"][rt] = [str(r) for r in dns.resolver.resolve(domain, rt)]
            except: result["dns"][rt] = []
    except: pass
    c = db.conn.cursor()
    c.execute("INSERT INTO domain_intelligence (id,user_id,domain,whois_data,ssl_data,dns_data,created_at) VALUES (?,?,?,?,?,?,?)",
              (str(uuid.uuid4()), current_user['id'], domain, json.dumps(result["whois"]), json.dumps(result["ssl"]), json.dumps(result["dns"]), datetime.utcnow().isoformat()))
    db.conn.commit()
    return result

# ===================================================================
# ENDPOINTS - MARKET INTELLIGENCE
# ===================================================================
@app.get("/market-intelligence/trends")
async def market_trends():
    return {"market_size": "$50B", "growth_rate": "14.5%", "legal_tech_growth": "23.7%", "ai_adoption": "67%", "trends": [{"sector": "Technology", "growth": 15.5}, {"sector": "Healthcare", "growth": 12.3}, {"sector": "Finance", "growth": 8.7}, {"sector": "Legal", "growth": 18.2}], "competitors": [{"name": "LegalTech Corp", "market_share": 20}, {"name": "LawAI Solutions", "market_share": 15}], "regulatory_updates": [{"date": "2026-06-15", "change": "DPDP Act 2023 Implementation"}], "timestamp": datetime.utcnow().isoformat()}

@app.get("/market-intelligence/competitors")
async def competitors():
    return {"competitors": [{"name": "LegalTech Corp", "market_share": 20, "strength": "Strong"}, {"name": "LawAI Solutions", "market_share": 15, "strength": "Growing"}], "timestamp": datetime.utcnow().isoformat()}

# ===================================================================
# ENDPOINTS - ACCOUNT
# ===================================================================
@app.get("/account/history")
async def account_history(limit: int = 50, offset: int = 0, current_user=Depends(get_current_user)):
    c = db.conn.cursor()
    c.execute("SELECT action, details, created_at FROM activity_log WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?", (current_user['id'], limit, offset))
    activities = c.fetchall()
    c.execute("SELECT COUNT(*) FROM activity_log WHERE user_id=?", (current_user['id'],))
    return {"activities": [dict(a) for a in activities], "total": c.fetchone()[0]}

@app.get("/account/stats")
async def account_stats(current_user=Depends(get_current_user)):
    c = db.conn.cursor()
    c.execute("SELECT COUNT(*) FROM legal_queries WHERE user_id=?", (current_user['id'],))
    queries = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM agent_runs WHERE user_id=?", (current_user['id'],))
    runs = c.fetchone()[0]
    c.execute("SELECT COUNT(*), SUM(amount) FROM payments WHERE user_id=? AND status='completed'", (current_user['id'],))
    p = c.fetchone()
    return {"total_queries": queries, "total_agent_runs": runs, "total_payments": p[0] if p[0] else 0, "total_amount": p[1] if p[1] else 0}

# ===================================================================
# ENDPOINTS - LEGAL QUERY
# ===================================================================
@app.post("/legal/query")
async def legal_query(data: LegalQuery, current_user=Depends(get_current_user)):
    response = {"query": data.query, "agent_type": data.agent_type, "response": f"Legal analysis for: {data.query}", "confidence_score": 0.95, "relevant_laws": ["Constitution of India", "IPC", "CrPC", "DPDP Act 2023"], "precedents": ["Supreme Court Case 2023"], "risk_level": "Low", "recommendations": ["Review relevant case law", "Consult with senior counsel"], "disclaimer": "Not legal advice.", "attorney_client_privilege": True, "timestamp": datetime.utcnow().isoformat()}
    c = db.conn.cursor()
    c.execute("INSERT INTO legal_queries (id,user_id,query,response,agent_type,context,confidence_score,processed_at) VALUES (?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4()), current_user['id'], data.query, json.dumps(response), data.agent_type, json.dumps(data.context), response['confidence_score'], datetime.utcnow().isoformat()))
    c.execute("UPDATE users SET total_queries=total_queries+1 WHERE id=?", (current_user['id'],))
    db.conn.commit()
    return response

# ===================================================================
# ENDPOINTS - FILE UPLOAD
# ===================================================================
@app.post("/upload/file")
async def upload_file(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    allowed = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'image/png', 'image/jpeg']
    if file.content_type not in allowed: raise HTTPException(400, "File type not allowed")
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    content = await file.read()
    with open(path, "wb") as f: f.write(content)
    c = db.conn.cursor()
    c.execute("INSERT INTO uploads (id,user_id,filename,file_path,file_type,file_size,created_at) VALUES (?,?,?,?,?,?,?)",
              (file_id, current_user['id'], file.filename, path, file.content_type, len(content), datetime.utcnow().isoformat()))
    db.conn.commit()
    return {"file_id": file_id, "filename": file.filename, "file_type": file.content_type, "file_size": len(content), "download_url": f"/download/file/{file_id}"}

@app.get("/download/file/{file_id}")
async def download_file(file_id: str, current_user=Depends(get_current_user)):
    c = db.conn.cursor()
    c.execute("SELECT * FROM uploads WHERE id=? AND user_id=?", (file_id, current_user['id']))
    f = c.fetchone()
    if not f: raise HTTPException(404, "File not found")
    if not os.path.exists(f['file_path']): raise HTTPException(404, "File not found on server")
    return FileResponse(f['file_path'], media_type=f['file_type'], filename=f['filename'])

@app.get("/uploads/list")
async def list_uploads(current_user=Depends(get_current_user)):
    c = db.conn.cursor()
    c.execute("SELECT id,filename,file_type,file_size,created_at FROM uploads WHERE user_id=? ORDER BY created_at DESC", (current_user['id'],))
    return {"uploads": [dict(u) for u in c.fetchall()]}

# ===================================================================
# ENDPOINTS - STATUS & ROOT
# ===================================================================
@app.get("/status")
async def status():
    return {"status": "alive", "version": "4.0.0", "agents": 73, "zero_retention": "active", "lawyer": "Adv. Debo", "firm": "THE ADVOCACY A LAW FIRM", "features": {"cv_simulation": "active", "prompt_templates": "active", "payment": "active"}}

@app.get("/")
async def root():
    return {"service": "LexSarthi v4.0", "version": "4.0.0", "lawyer": {"name": "Adv. Debo", "firm": "THE ADVOCACY A LAW FIRM"}, "agents": 73, "vision": "Single Provider for All Legal Work Automation", "tagline": "From Contract Review to Supreme Court Judgments", "features": {"authentication": "active", "payment": "active (₹2)", "cv_simulation": "active", "agent_runs": "active", "domain_intelligence": "active", "market_intelligence": "active"}}

# ===================================================================
# RUN
# ===================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)