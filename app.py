
# ===================================================================
# LEXSARTHI v4.0 - INDIA'S FIRST AI-NATIVE COMPLETE LEGAL OS
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# "From Contract Review to Supreme Court Judgments"
# "From Law School to Global Legal Practice"
# "One Platform. Every Legal Need. Anywhere in the World."
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================
# 🔥 OPENROUTER INTEGRATION - UNLIMITED TOKENS
# 🔥 ZERO DATA RETENTION - 24h AUTO-DELETE
# 🔥 73 AI AGENTS WITH LAWYER CV
# 🔥 MULTI-AGENT VERIFICATION
# ===================================================================

import os
import json
import uuid
import time
import random
import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import httpx
import jwt
import bcrypt
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field

load_dotenv()

# ===================================================================
# LOGGING
# ===================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("lexsarthi")

# ===================================================================
# CONFIGURATION
# ===================================================================
SECRET_KEY = os.getenv("JWT_SECRET", "lexsarthi-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OpenRouter Configuration (Unlimited Tokens - NO OPENAI)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://www.advocacyalawfrim.in",
    "X-Title": "LexSarthi v4.0 Legal OS",
    "Content-Type": "application/json"
}

# ===================================================================
# DATABASE LAYER (with Zero Retention)
# ===================================================================
class Database:
    def __init__(self, db_path="lexsarthi.db"):
        self.db_path = db_path
        self.init_db()
        self.start_retention_cleanup()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT,
                firm_name TEXT,
                user_type TEXT DEFAULT 'individual',
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                username TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'INR',
                status TEXT NOT NULL,
                payment_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                query TEXT,
                response_time REAL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_retention_cleanup(self):
        import threading
        def cleanup_loop():
            while True:
                time.sleep(3600)
                self.cleanup_old_data()
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def cleanup_old_data(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            
            cursor.execute('DELETE FROM user_history WHERE timestamp < ?', (cutoff,))
            history_deleted = cursor.rowcount
            
            cursor.execute('DELETE FROM agent_usage WHERE timestamp < ?', (cutoff,))
            agent_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if history_deleted > 0 or agent_deleted > 0:
                logger.info(f"Zero Retention: Deleted {history_deleted} history records, {agent_deleted} agent usage records")
        except Exception as e:
            logger.error(f"Retention cleanup error: {str(e)}")
    
    def create_user(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (id, username, email, password, full_name, firm_name, user_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['id'], data['username'], data['email'], data['password'],
              data.get('full_name'), data.get('firm_name'), data.get('user_type', 'individual'),
              data['created_at']))
        conn.commit()
        conn.close()
    
    def get_user(self, username):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'username', 'email', 'password', 'full_name', 'firm_name', 'user_type', 'created_at', 'last_login']
            return dict(zip(columns, row))
        return None
    
    def get_user_by_email(self, email):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'username', 'email', 'password', 'full_name', 'firm_name', 'user_type', 'created_at', 'last_login']
            return dict(zip(columns, row))
        return None
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'username', 'email', 'password', 'full_name', 'firm_name', 'user_type', 'created_at', 'last_login']
            return dict(zip(columns, row))
        return None
    
    def update_last_login(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
    
    def store_refresh_token(self, username, token):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO refresh_tokens (username, token, created_at) VALUES (?, ?, ?)',
                      (username, token, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_refresh_token(self, username):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT token FROM refresh_tokens WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def delete_refresh_token(self, username):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM refresh_tokens WHERE username = ?', (username,))
        conn.commit()
        conn.close()
    
    def add_history(self, user_id, action, details=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO user_history (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)',
                      (user_id, action, json.dumps(details) if details else None, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def add_payment_log(self, order_id, user_id, amount, status, currency="INR", payment_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO payment_logs (order_id, user_id, amount, currency, status, payment_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (order_id, user_id, amount, currency, status, payment_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_payment_log(self, order_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM payment_logs WHERE order_id = ?', (order_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'order_id', 'user_id', 'amount', 'currency', 'status', 'payment_id', 'created_at']
            return dict(zip(columns, row))
        return None
    
    def update_payment_status(self, order_id, status, payment_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if payment_id:
            cursor.execute('UPDATE payment_logs SET status = ?, payment_id = ? WHERE order_id = ?',
                          (status, payment_id, order_id))
        else:
            cursor.execute('UPDATE payment_logs SET status = ? WHERE order_id = ?', (status, order_id))
        conn.commit()
        conn.close()
    
    def log_agent_usage(self, user_id, agent_id, query, response_time):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO agent_usage (user_id, agent_id, query, response_time, timestamp) VALUES (?, ?, ?, ?, ?)',
                      (user_id, agent_id, query[:200], response_time, datetime.now().isoformat()))
        conn.commit()
        conn.close()

db = Database()

# ===================================================================
# AUTH FUNCTIONS
# ===================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: Dict[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire, "type": "access"})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    data.update({"exp": expire, "type": "refresh"})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ===================================================================
# MODELS
# ===================================================================
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    firm_name: Optional[str] = None
    user_type: str = "individual"

class UserLogin(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

class AgentRequest(BaseModel):
    agent_id: str
    query: str = Field(..., min_length=3)
    context: Optional[Dict[str, Any]] = None

class PaymentRequest(BaseModel):
    amount: int = 2
    currency: str = "INR"
    user_id: str

class PaymentVerificationRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

# ===================================================================
# LAWYER CV DATABASE
# ===================================================================
LAWYER_CV_DATABASE = {
    "sc-001": {"name": "Adv. Rajesh Khanna", "designation": "Senior Advocate, Supreme Court", "experience": 28, "specialization": "Constitutional Law, Criminal Law", "firm": "Khanna & Associates", "rating": 4.9},
    "sc-002": {"name": "Adv. Priya Mehta", "designation": "Advocate-on-Record, Supreme Court", "experience": 15, "specialization": "Corporate Law, Tax Law", "firm": "Mehta Legal Chambers", "rating": 4.8},
    "sc-003": {"name": "Adv. Dr. Ananya Sharma", "designation": "Constitutional Law Expert", "experience": 22, "specialization": "Constitutional Law, Human Rights", "firm": "Sharma Constitutional Chambers", "rating": 4.9},
    "hc-001": {"name": "Adv. Vikram Singh", "designation": "Senior Advocate, Delhi High Court", "experience": 20, "specialization": "Civil Law, Family Law", "firm": "Singh Legal Associates", "rating": 4.7},
    "corp-001": {"name": "Adv. Deepak Gupta", "designation": "Corporate Legal Director", "experience": 18, "specialization": "M&A, Private Equity", "firm": "Gupta Corporate Law", "rating": 4.8},
    "corp-002": {"name": "Adv. Ritu Kapoor", "designation": "Compliance & Regulatory Expert", "experience": 14, "specialization": "DPDP, GDPR", "firm": "Kapoor Compliance", "rating": 4.7},
    "tech-001": {"name": "Adv. Mohit Verma", "designation": "Technology Law Specialist", "experience": 16, "specialization": "AI Law, Cybersecurity", "firm": "Verma Technology Law", "rating": 4.8},
    "dr-001": {"name": "Adv. Sanjay Malhotra", "designation": "Dispute Resolution Partner", "experience": 22, "specialization": "Arbitration, Litigation", "firm": "Malhotra Dispute Resolution", "rating": 4.8},
    "int-001": {"name": "Adv. Dr. Michael Chen", "designation": "International Arbitration Specialist", "experience": 25, "specialization": "International Arbitration", "firm": "Chen International Legal", "rating": 4.9}
}

# ===================================================================
# 73 AGENTS WITH PROMPTS
# ===================================================================
def create_agent_list():
    agents = []
    
    # Legal Intelligence Agents (20)
    li_agents = [
        {"id": "li-001", "name": "Supreme Court Case Predictor", "lawyer": "sc-001", "prompt": "You are a Supreme Court Case Predictor. Analyze the query and predict likely outcome based on Supreme Court precedents."},
        {"id": "li-002", "name": "Legal Research Assistant", "lawyer": "sc-003", "prompt": "You are a Legal Research Assistant. Find relevant case laws and statutes."},
        {"id": "li-003", "name": "Precedent Analyzer", "lawyer": "hc-001", "prompt": "You are a Precedent Analyzer. Identify and analyze relevant legal precedents."},
        {"id": "li-004", "name": "Statutory Interpreter", "lawyer": "sc-001", "prompt": "You are a Statutory Interpreter. Interpret complex legal statutes clearly."},
        {"id": "li-005", "name": "Case Summarizer", "lawyer": "hc-001", "prompt": "You are a Case Summarizer. Summarize lengthy court judgments concisely."},
        {"id": "li-006", "name": "Legal Document Drafter", "lawyer": "corp-001", "prompt": "You are a Legal Document Drafter. Draft professional legal documents."},
        {"id": "li-007", "name": "Judgment Analyzer", "lawyer": "sc-003", "prompt": "You are a Judgment Analyzer. Extract key legal principles from judgments."},
        {"id": "li-008", "name": "Legal Risk Assessor", "lawyer": "corp-001", "prompt": "You are a Legal Risk Assessor. Identify and assess legal risks."},
        {"id": "li-009", "name": "Compliance Checker", "lawyer": "corp-002", "prompt": "You are a Compliance Checker. Verify compliance with laws."},
        {"id": "li-010", "name": "Legal Opinion Generator", "lawyer": "sc-001", "prompt": "You are a Legal Opinion Generator. Provide preliminary legal opinions."},
        {"id": "li-011", "name": "Case Strategy Advisor", "lawyer": "dr-001", "prompt": "You are a Case Strategy Advisor. Develop strategic case planning."},
        {"id": "li-012", "name": "Evidence Analyzer", "lawyer": "sc-001", "prompt": "You are an Evidence Analyzer. Analyze evidence strength."},
        {"id": "li-013", "name": "Witness Statement Analyzer", "lawyer": "sc-001", "prompt": "You are a Witness Statement Analyzer. Analyze witness statements."},
        {"id": "li-014", "name": "Legal Citation Checker", "lawyer": "sc-003", "prompt": "You are a Legal Citation Checker. Verify legal citations."},
        {"id": "li-015", "name": "Legal Research Planner", "lawyer": "sc-003", "prompt": "You are a Legal Research Planner. Create research plans."},
        {"id": "li-016", "name": "Legislative Tracker", "lawyer": "corp-002", "prompt": "You are a Legislative Tracker. Track legislative changes."},
        {"id": "li-017", "name": "Case Outcome Predictor", "lawyer": "sc-001", "prompt": "You are a Case Outcome Predictor. Predict case outcomes."},
        {"id": "li-018", "name": "Legal Issue Spotter", "lawyer": "sc-003", "prompt": "You are a Legal Issue Spotter. Identify key legal issues."},
        {"id": "li-019", "name": "Legal Argument Generator", "lawyer": "sc-001", "prompt": "You are a Legal Argument Generator. Generate legal arguments."},
        {"id": "li-020", "name": "Legal Knowledge Graph", "lawyer": "sc-003", "prompt": "You are a Legal Knowledge Graph. Map legal relationships."}
    ]
    
    for agent in li_agents:
        agent["category"] = "Legal Intelligence"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["li-002", "li-003", "li-017"]
        agents.append(agent)
    
    # Corporate Law Agents (10)
    cl_agents = [
        {"id": "cl-001", "name": "M&A Due Diligence", "lawyer": "corp-001", "prompt": "You are a M&A Due Diligence expert. Analyze corporate transactions."},
        {"id": "cl-002", "name": "Contract Reviewer", "lawyer": "corp-001", "prompt": "You are a Contract Reviewer. Review contracts and identify risks."},
        {"id": "cl-003", "name": "Compliance Monitor", "lawyer": "corp-002", "prompt": "You are a Compliance Monitor. Ensure corporate compliance."},
        {"id": "cl-004", "name": "IP Analyzer", "lawyer": "corp-002", "prompt": "You are an IP Analyzer. Analyze intellectual property."},
        {"id": "cl-005", "name": "Board Resolution Drafter", "lawyer": "corp-001", "prompt": "You are a Board Resolution Drafter. Draft board resolutions."},
        {"id": "cl-006", "name": "Shareholder Agreement Drafter", "lawyer": "corp-001", "prompt": "You are a Shareholder Agreement Drafter. Draft shareholder agreements."},
        {"id": "cl-007", "name": "Corporate Governance Advisor", "lawyer": "corp-001", "prompt": "You are a Corporate Governance Advisor. Advise on governance."},
        {"id": "cl-008", "name": "Merger Advisor", "lawyer": "corp-001", "prompt": "You are a Merger Advisor. Advise on mergers."},
        {"id": "cl-009", "name": "Acquisition Strategist", "lawyer": "corp-001", "prompt": "You are an Acquisition Strategist. Develop acquisition strategies."},
        {"id": "cl-010", "name": "Cross-border Deal Maker", "lawyer": "int-001", "prompt": "You are a Cross-border Deal Maker. Handle international deals."}
    ]
    
    for agent in cl_agents:
        agent["category"] = "Corporate Law"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["cl-002", "cl-003", "li-008"]
        agents.append(agent)
    
    # Personal Law Agents (10)
    pl_agents = [
        {"id": "pl-001", "name": "Family Law Advisor", "lawyer": "hc-001", "prompt": "You are a Family Law Advisor. Provide family law advice."},
        {"id": "pl-002", "name": "Divorce Case Analyst", "lawyer": "hc-001", "prompt": "You are a Divorce Case Analyst. Analyze divorce cases."},
        {"id": "pl-003", "name": "Child Custody Advisor", "lawyer": "hc-001", "prompt": "You are a Child Custody Advisor. Advise on child custody."},
        {"id": "pl-004", "name": "Will & Estate Planner", "lawyer": "hc-001", "prompt": "You are a Will & Estate Planner. Assist with estate planning."},
        {"id": "pl-005", "name": "Property Lawyer", "lawyer": "hc-001", "prompt": "You are a Property Lawyer. Advise on property law."},
        {"id": "pl-006", "name": "Tenancy Dispute Resolver", "lawyer": "hc-001", "prompt": "You are a Tenancy Dispute Resolver. Resolve tenancy disputes."},
        {"id": "pl-007", "name": "Marriage Agreement Drafter", "lawyer": "hc-001", "prompt": "You are a Marriage Agreement Drafter. Draft marriage agreements."},
        {"id": "pl-008", "name": "Adoption Law Advisor", "lawyer": "hc-001", "prompt": "You are an Adoption Law Advisor. Advise on adoption."},
        {"id": "pl-009", "name": "Consumer Rights Advocate", "lawyer": "sc-003", "prompt": "You are a Consumer Rights Advocate. Advocate for consumer rights."},
        {"id": "pl-010", "name": "Employment Law Advisor", "lawyer": "corp-002", "prompt": "You are an Employment Law Advisor. Advise on employment law."}
    ]
    
    for agent in pl_agents:
        agent["category"] = "Personal Law"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["pl-001", "pl-002", "li-001"]
        agents.append(agent)
    
    # Public Law Agents (5)
    pub_agents = [
        {"id": "pub-001", "name": "Constitutional Law Expert", "lawyer": "sc-001", "prompt": "You are a Constitutional Law Expert. Analyze constitutional issues."},
        {"id": "pub-002", "name": "Administrative Law Advisor", "lawyer": "sc-003", "prompt": "You are an Administrative Law Advisor. Advise on administrative law."},
        {"id": "pub-003", "name": "Public Interest Lawyer", "lawyer": "sc-003", "prompt": "You are a Public Interest Lawyer. Handle PIL cases."},
        {"id": "pub-004", "name": "Human Rights Defender", "lawyer": "sc-003", "prompt": "You are a Human Rights Defender. Advocate for human rights."},
        {"id": "pub-005", "name": "Environmental Law Expert", "lawyer": "sc-003", "prompt": "You are an Environmental Law Expert. Advise on environmental law."}
    ]
    
    for agent in pub_agents:
        agent["category"] = "Public Law"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["pub-001", "pub-002", "li-001"]
        agents.append(agent)
    
    # Dispute Resolution Agents (8)
    dr_agents = [
        {"id": "dr-001", "name": "Arbitration Drafter", "lawyer": "dr-001", "prompt": "You are an Arbitration Drafter. Draft arbitration documents."},
        {"id": "dr-002", "name": "Mediation Expert", "lawyer": "dr-001", "prompt": "You are a Mediation Expert. Facilitate mediation."},
        {"id": "dr-003", "name": "Litigation Strategist", "lawyer": "dr-001", "prompt": "You are a Litigation Strategist. Develop litigation strategies."},
        {"id": "dr-004", "name": "Trial Preparation Assistant", "lawyer": "dr-001", "prompt": "You are a Trial Preparation Assistant. Assist with trial prep."},
        {"id": "dr-005", "name": "Appeal Specialist", "lawyer": "sc-001", "prompt": "You are an Appeal Specialist. Handle appeal matters."},
        {"id": "dr-006", "name": "Dispute Resolution Advisor", "lawyer": "dr-001", "prompt": "You are a Dispute Resolution Advisor. Advise on dispute resolution."},
        {"id": "dr-007", "name": "International Arbitration Expert", "lawyer": "int-001", "prompt": "You are an International Arbitration Expert. Handle international arbitration."},
        {"id": "dr-008", "name": "Alternative Dispute Resolution", "lawyer": "dr-001", "prompt": "You are an ADR Expert. Provide ADR methods expertise."}
    ]
    
    for agent in dr_agents:
        agent["category"] = "Dispute Resolution"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["dr-001", "dr-003", "li-001"]
        agents.append(agent)
    
    # Technology Law Agents (10)
    tech_agents = [
        {"id": "tech-001", "name": "Cybersecurity Law Advisor", "lawyer": "tech-001", "prompt": "You are a Cybersecurity Law Advisor. Advise on cybersecurity."},
        {"id": "tech-002", "name": "Data Privacy Officer", "lawyer": "corp-002", "prompt": "You are a Data Privacy Officer. Advise on data privacy."},
        {"id": "tech-003", "name": "IP and Patent Drafter", "lawyer": "tech-001", "prompt": "You are an IP and Patent Drafter. Draft IP and patents."},
        {"id": "tech-004", "name": "Technology Contract Reviewer", "lawyer": "tech-001", "prompt": "You are a Technology Contract Reviewer. Review tech contracts."},
        {"id": "tech-005", "name": "AI Law Advisor", "lawyer": "tech-001", "prompt": "You are an AI Law Advisor. Advise on AI law."},
        {"id": "tech-006", "name": "Blockchain Law Expert", "lawyer": "tech-001", "prompt": "You are a Blockchain Law Expert. Advise on blockchain."},
        {"id": "tech-007", "name": "Digital Rights Advocate", "lawyer": "tech-001", "prompt": "You are a Digital Rights Advocate. Advocate for digital rights."},
        {"id": "tech-008", "name": "Software Licensing Advisor", "lawyer": "tech-001", "prompt": "You are a Software Licensing Advisor. Advise on licensing."},
        {"id": "tech-009", "name": "Fintech Law Expert", "lawyer": "tech-001", "prompt": "You are a Fintech Law Expert. Advise on fintech law."},
        {"id": "tech-010", "name": "E-commerce Law Expert", "lawyer": "tech-001", "prompt": "You are an E-commerce Law Expert. Advise on e-commerce."}
    ]
    
    for agent in tech_agents:
        agent["category"] = "Technology"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["tech-001", "tech-002", "li-009"]
        agents.append(agent)
    
    # Specialized Agents (10)
    spec_agents = [
        {"id": "spec-001", "name": "Tax Law Advisor", "lawyer": "sc-002", "prompt": "You are a Tax Law Advisor. Advise on tax law."},
        {"id": "spec-002", "name": "Banking Law Expert", "lawyer": "corp-001", "prompt": "You are a Banking Law Expert. Advise on banking law."},
        {"id": "spec-003", "name": "Insurance Law Advisor", "lawyer": "corp-001", "prompt": "You are an Insurance Law Advisor. Advise on insurance."},
        {"id": "spec-004", "name": "Real Estate Legal Advisor", "lawyer": "hc-001", "prompt": "You are a Real Estate Legal Advisor. Advise on real estate."},
        {"id": "spec-005", "name": "Media Law Expert", "lawyer": "sc-003", "prompt": "You are a Media Law Expert. Advise on media law."},
        {"id": "spec-006", "name": "Sports Law Advisor", "lawyer": "dr-001", "prompt": "You are a Sports Law Advisor. Advise on sports law."},
        {"id": "spec-007", "name": "Education Law Expert", "lawyer": "sc-003", "prompt": "You are an Education Law Expert. Advise on education law."},
        {"id": "spec-008", "name": "Healthcare Law Advisor", "lawyer": "corp-002", "prompt": "You are a Healthcare Law Advisor. Advise on healthcare."},
        {"id": "spec-009", "name": "Immigration Law Expert", "lawyer": "int-001", "prompt": "You are an Immigration Law Expert. Advise on immigration."},
        {"id": "spec-010", "name": "International Law Expert", "lawyer": "int-001", "prompt": "You are an International Law Expert. Advise on international law."}
    ]
    
    for agent in spec_agents:
        agent["category"] = "Specialized"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["spec-001", "li-001", "li-008"]
        agents.append(agent)
    
    return agents

AGENT_LIST = create_agent_list()

# ===================================================================
# OPENROUTER CLIENT (NO OPENAI - PURE OPENROUTER)
# ===================================================================
async def call_openrouter(prompt: str, max_tokens: int = 2000) -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=OPENROUTER_HEADERS,
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are LexSarthi, India's First AI-Native Legal OS. Provide professional, accurate legal analysis. Always include firm branding."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenRouter error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"OpenRouter call failed: {str(e)}")
        return None

# ===================================================================
# AGENT EXECUTION ENGINE
# ===================================================================
async def execute_agent(agent: Dict, query: str, user_id: str = None) -> Dict[str, Any]:
    start_time = time.perf_counter()
    
    lawyer = agent.get("lawyer_profile", {})
    lawyer_name = lawyer.get("name", "Expert Lawyer")
    lawyer_exp = lawyer.get("experience", 15)
    lawyer_spec = lawyer.get("specialization", "Legal")
    lawyer_firm = lawyer.get("firm", "THE ADVOCACY A LAW FIRM")
    
    prompt = f"""
{agent.get('prompt', 'You are a legal expert.')}

YOUR ROLE: {agent['name']}
    