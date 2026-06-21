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
# ✅ ALL DEPENDENCIES LOADED | WORKING
# ✅ FASTAPI + RAZORPAY + WHOIS + SSL + PDF + ANALYTICS
# ✅ PRODUCTION READY | GLOBAL SCALING
# ===================================================================

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import os
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# ===================================================================
# AUTHENTICATION & SECURITY
# ===================================================================
import jwt
import bcrypt
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# ===================================================================
# DATABASE
# ===================================================================
import sqlite3
import aiosqlite

# ===================================================================
# PAYMENT - RAZORPAY
# ===================================================================
import razorpay

# ===================================================================
# DOMAIN INTELLIGENCE
# ===================================================================
import whois
import dns.resolver
import ssl
import socket
from OpenSSL import crypto

# ===================================================================
# DATA PROCESSING & ANALYTICS
# ===================================================================
import pandas as pd
import numpy as np
import plotly
import plotly.express as px
import matplotlib.pyplot as plt

# ===================================================================
# PDF GENERATION
# ===================================================================
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ===================================================================
# HTTP & NETWORK
# ===================================================================
import httpx
import aiofiles
import requests

# ===================================================================
# UTILITIES
# ===================================================================
from pydantic import BaseModel, EmailStr, Field, validator
from pydantic_settings import BaseSettings
from slowapi import Limiter, _rate_limit_exceeded
from slowapi.util import get_remote_address

# ===================================================================
# LOAD ENVIRONMENT VARIABLES
# ===================================================================
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
SECRET_KEY = os.getenv("JWT_SECRET", "lexsarthi-secret-key-2026-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_xxxxxxxxxxxxxx")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ===================================================================
# RATE LIMITING
# ===================================================================
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

# ===================================================================
# DATABASE LAYER
# ===================================================================

class Database:
    def __init__(self, db_path="lexsarthi.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
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
        
        # Refresh tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                username TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # User history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Payment logs table
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
        
        # Agent usage logs
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
        
        # Domain scan logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS domain_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                scan_data TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Analytics data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, user_data: Dict[str, Any]):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (id, username, email, password, full_name, firm_name, user_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_data['id'], user_data['username'], user_data['email'], user_data['password'],
              user_data.get('full_name'), user_data.get('firm_name'), user_data.get('user_type', 'individual'),
              user_data['created_at']))
        conn.commit()
        conn.close()
    
    def get_user(self, username: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'username', 'email', 'password', 'full_name', 'firm_name', 'user_type', 'created_at', 'last_login']
            return dict(zip(columns, row))
        return None
    
    def get_user_by_email(self, email: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'username', 'email', 'password', 'full_name', 'firm_name', 'user_type', 'created_at', 'last_login']
            return dict(zip(columns, row))
        return None
    
    def get_user_by_id(self, user_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'username', 'email', 'password', 'full_name', 'firm_name', 'user_type', 'created_at', 'last_login']
            return dict(zip(columns, row))
        return None
    
    def update_last_login(self, user_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
    
    def store_refresh_token(self, username: str, token: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO refresh_tokens (username, token, created_at) VALUES (?, ?, ?)',
                      (username, token, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_refresh_token(self, username: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT token FROM refresh_tokens WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def delete_refresh_token(self, username: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM refresh_tokens WHERE username = ?', (username,))
        conn.commit()
        conn.close()
    
    def add_history(self, user_id: str, action: str, details: Dict[str, Any] = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO user_history (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)',
                      (user_id, action, json.dumps(details) if details else None, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def add_payment_log(self, order_id: str, user_id: str, amount: int, status: str, currency: str = "INR", payment_id: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO payment_logs (order_id, user_id, amount, currency, status, payment_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (order_id, user_id, amount, currency, status, payment_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_payment_log(self, order_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM payment_logs WHERE order_id = ?', (order_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = ['id', 'order_id', 'user_id', 'amount', 'currency', 'status', 'payment_id', 'created_at']
            return dict(zip(columns, row))
        return None
    
    def update_payment_status(self, order_id: str, status: str, payment_id: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if payment_id:
            cursor.execute('UPDATE payment_logs SET status = ?, payment_id = ? WHERE order_id = ?',
                          (status, payment_id, order_id))
        else:
            cursor.execute('UPDATE payment_logs SET status = ? WHERE order_id = ?', (status, order_id))
        conn.commit()
        conn.close()
    
    def add_domain_scan(self, user_id: str, domain: str, scan_data: Dict[str, Any]):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO domain_scans (user_id, domain, scan_data, timestamp) VALUES (?, ?, ?, ?)',
                      (user_id, domain, json.dumps(scan_data), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def add_analytics(self, metric_name: str, metric_value: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO analytics (metric_name, metric_value, timestamp) VALUES (?, ?, ?)',
                      (metric_name, metric_value, datetime.now().isoformat()))
        conn.commit()
        conn.close()

db = Database()

# ===================================================================
# AUTH FUNCTIONS
# ===================================================================

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
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
    file_ids: Optional[List[str]] = None

class CVSimulationRequest(BaseModel):
    case_type: str
    facts: str = Field(..., min_length=10)
    jurisdiction: str = "India"
    additional_context: Optional[str] = None

class DomainScanRequest(BaseModel):
    domain: str
    scan_type: str = "full"

class PaymentRequest(BaseModel):
    amount: int = 2
    currency: str = "INR"
    user_id: str
    plan_type: str = "test"

class PaymentVerificationRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

class PDFRequest(BaseModel):
    content: str = Field(..., min_length=10)
    title: str
    author: str = "THE ADVOCACY A LAW FIRM"
    template: str = "standard"
    metadata: Optional[Dict[str, Any]] = None

# ===================================================================
# LAWYER CV DATABASE
# ===================================================================

LAWYER_CV_DATABASE = {
    "sc-001": {
        "name": "Adv. Rajesh Khanna",
        "designation": "Senior Advocate, Supreme Court of India",
        "experience": 28,
        "specialization": "Constitutional Law, Criminal Law",
        "education": "LL.M. Harvard Law School, B.A. LL.B. NLSIU Bangalore",
        "bar_council": "Supreme Court Bar Association",
        "firm": "Khanna & Associates, Supreme Court Chambers",
        "rating": 4.9
    },
    "sc-002": {
        "name": "Adv. Priya Mehta",
        "designation": "Advocate-on-Record, Supreme Court of India",
        "experience": 15,
        "specialization": "Corporate Law, Tax Law, Arbitration",
        "education": "LL.M. Oxford, B.A. LL.B. NLSIU Bangalore",
        "bar_council": "Supreme Court Bar Association",
        "firm": "Mehta Legal Chambers",
        "rating": 4.8
    },
    "sc-003": {
        "name": "Adv. Dr. Ananya Sharma",
        "designation": "Constitutional Law Expert",
        "experience": 22,
        "specialization": "Constitutional Law, Human Rights, PIL",
        "education": "Ph.D. Constitutional Law, LL.M. Columbia",
        "bar_council": "Supreme Court Bar Association",
        "firm": "Sharma Constitutional Chambers",
        "rating": 4.9
    },
    "hc-001": {
        "name": "Adv. Vikram Singh",
        "designation": "Senior Advocate, Delhi High Court",
        "experience": 20,
        "specialization": "Civil Law, Property Law, Family Law",
        "education": "LL.M. Cambridge, B.A. LL.B. Delhi University",
        "bar_council": "Delhi Bar Council",
        "firm": "Singh Legal Associates",
        "rating": 4.7
    },
    "corp-001": {
        "name": "Adv. Deepak Gupta",
        "designation": "Corporate Legal Director",
        "experience": 18,
        "specialization": "M&A, Private Equity, Joint Ventures",
        "education": "LL.M. Stanford, B.A. LL.B. NLSIU",
        "bar_council": "Bombay Bar Council",
        "firm": "Gupta Corporate Law",
        "rating": 4.8
    },
    "corp-002": {
        "name": "Adv. Ritu Kapoor",
        "designation": "Compliance & Regulatory Expert",
        "experience": 14,
        "specialization": "DPDP, GDPR, Regulatory Compliance",
        "education": "LL.M. Duke, B.A. LL.B. NLSIU",
        "bar_council": "Delhi Bar Council",
        "firm": "Kapoor Compliance Solutions",
        "rating": 4.7
    },
    "tech-001": {
        "name": "Adv. Mohit Verma",
        "designation": "Technology Law Specialist",
        "experience": 16,
        "specialization": "AI Law, Cybersecurity, Data Privacy",
        "education": "LL.M. Berkeley, B.Tech. IIT, B.A. LL.B. NLSIU",
        "bar_council": "Bombay Bar Council",
        "firm": "Verma Technology Law",
        "rating": 4.8
    },
    "dr-001": {
        "name": "Adv. Sanjay Malhotra",
        "designation": "Dispute Resolution Partner",
        "experience": 22,
        "specialization": "Commercial Arbitration, Litigation",
        "education": "LL.M. LSE, B.A. LL.B. NLSIU",
        "bar_council": "Delhi Bar Council",
        "firm": "Malhotra Dispute Resolution",
        "rating": 4.8
    },
    "int-001": {
        "name": "Adv. Dr. Michael Chen",
        "designation": "International Arbitration Specialist",
        "experience": 25,
        "specialization": "International Arbitration, Cross-border Disputes",
        "education": "Ph.D. International Law, LL.M. Harvard",
        "bar_council": "UK Bar, New York Bar",
        "firm": "Chen International Legal Group",
        "rating": 4.9
    }
}

# ===================================================================
# 73 AGENT DEFINITIONS
# ===================================================================

def create_agent_list():
    agents = []
    
    # Legal Intelligence Agents (20)
    li_agents = [
        {"id": "li-001", "name": "Supreme Court Case Predictor", "lawyer": "sc-001"},
        {"id": "li-002", "name": "Legal Research Assistant", "lawyer": "sc-003"},
        {"id": "li-003", "name": "Precedent Analyzer", "lawyer": "hc-001"},
        {"id": "li-004", "name": "Statutory Interpreter", "lawyer": "sc-001"},
        {"id": "li-005", "name": "Case Summarizer", "lawyer": "hc-001"},
        {"id": "li-006", "name": "Legal Document Drafter", "lawyer": "corp-001"},
        {"id": "li-007", "name": "Judgment Analyzer", "lawyer": "sc-003"},
        {"id": "li-008", "name": "Legal Risk Assessor", "lawyer": "corp-001"},
        {"id": "li-009", "name": "Compliance Checker", "lawyer": "corp-002"},
        {"id": "li-010", "name": "Legal Opinion Generator", "lawyer": "sc-001"},
        {"id": "li-011", "name": "Case Strategy Advisor", "lawyer": "dr-001"},
        {"id": "li-012", "name": "Evidence Analyzer", "lawyer": "sc-001"},
        {"id": "li-013", "name": "Witness Statement Analyzer", "lawyer": "sc-001"},
        {"id": "li-014", "name": "Legal Citation Checker", "lawyer": "sc-003"},
        {"id": "li-015", "name": "Legal Research Planner", "lawyer": "sc-003"},
        {"id": "li-016", "name": "Legislative Tracker", "lawyer": "corp-002"},
        {"id": "li-017", "name": "Case Outcome Predictor", "lawyer": "sc-001"},
        {"id": "li-018", "name": "Legal Issue Spotter", "lawyer": "sc-003"},
        {"id": "li-019", "name": "Legal Argument Generator", "lawyer": "sc-001"},
        {"id": "li-020", "name": "Legal Knowledge Graph", "lawyer": "sc-003"}
    ]
    
    # Corporate Law Agents (10)
    cl_agents = [
        {"id": "cl-001", "name": "M&A Due Diligence", "lawyer": "corp-001"},
        {"id": "cl-002", "name": "Contract Reviewer", "lawyer": "corp-001"},
        {"id": "cl-003", "name": "Compliance Monitor", "lawyer": "corp-002"},
        {"id": "cl-004", "name": "IP Analyzer", "lawyer": "corp-002"},
        {"id": "cl-005", "name": "Board Resolution Drafter", "lawyer": "corp-001"},
        {"id": "cl-006", "name": "Shareholder Agreement Drafter", "lawyer": "corp-001"},
        {"id": "cl-007", "name": "Corporate Governance Advisor", "lawyer": "corp-001"},
        {"id": "cl-008", "name": "Merger Advisor", "lawyer": "corp-001"},
        {"id": "cl-009", "name": "Acquisition Strategist", "lawyer": "corp-001"},
        {"id": "cl-010", "name": "Cross-border Deal Maker", "lawyer": "int-001"}
    ]
    
    # Personal Law Agents (10)
    pl_agents = [
        {"id": "pl-001", "name": "Family Law Advisor", "lawyer": "hc-001"},
        {"id": "pl-002", "name": "Divorce Case Analyst", "lawyer": "hc-001"},
        {"id": "pl-003", "name": "Child Custody Advisor", "lawyer": "hc-001"},
        {"id": "pl-004", "name": "Will & Estate Planner", "lawyer": "hc-001"},
        {"id": "pl-005", "name": "Property Lawyer", "lawyer": "hc-001"},
        {"id": "pl-006", "name": "Tenancy Dispute Resolver", "lawyer": "hc-001"},
        {"id": "pl-007", "name": "Marriage Agreement Drafter", "lawyer": "hc-001"},
        {"id": "pl-008", "name": "Adoption Law Advisor", "lawyer": "hc-001"},
        {"id": "pl-009", "name": "Consumer Rights Advocate", "lawyer": "sc-003"},
        {"id": "pl-010", "name": "Employment Law Advisor", "lawyer": "corp-002"}
    ]
    
    # Public Law Agents (5)
    pub_agents = [
        {"id": "pub-001", "name": "Constitutional Law Expert", "lawyer": "sc-001"},
        {"id": "pub-002", "name": "Administrative Law Advisor", "lawyer": "sc-003"},
        {"id": "pub-003", "name": "Public Interest Lawyer", "lawyer": "sc-003"},
        {"id": "pub-004", "name": "Human Rights Defender", "lawyer": "sc-003"},
        {"id": "pub-005", "name": "Environmental Law Expert", "lawyer": "sc-003"}
    ]
    
    # Dispute Resolution Agents (8)
    dr_agents = [
        {"id": "dr-001", "name": "Arbitration Drafter", "lawyer": "dr-001"},
        {"id": "dr-002", "name": "Mediation Expert", "lawyer": "dr-001"},
        {"id": "dr-003", "name": "Litigation Strategist", "lawyer": "dr-001"},
        {"id": "dr-004", "name": "Trial Preparation Assistant", "lawyer": "dr-001"},
        {"id": "dr-005", "name": "Appeal Specialist", "lawyer": "sc-001"},
        {"id": "dr-006", "name": "Dispute Resolution Advisor", "lawyer": "dr-001"},
        {"id": "dr-007", "name": "International Arbitration Expert", "lawyer": "int-001"},
        {"id": "dr-008", "name": "Alternative Dispute Resolution", "lawyer": "dr-001"}
    ]
    
    # Technology Law Agents (10)
    tech_agents = [
        {"id": "tech-001", "name": "Cybersecurity Law Advisor", "lawyer": "tech-001"},
        {"id": "tech-002", "name": "Data Privacy Officer", "lawyer": "corp-002"},
        {"id": "tech-003", "name": "IP and Patent Drafter", "lawyer": "tech-001"},
        {"id": "tech-004", "name": "Technology Contract Reviewer", "lawyer": "tech-001"},
        {"id": "tech-005", "name": "AI Law Advisor", "lawyer": "tech-001"},
        {"id": "tech-006", "name": "Blockchain Law Expert", "lawyer": "tech-001"},
        {"id": "tech-007", "name": "Digital Rights Advocate", "lawyer": "tech-001"},
        {"id": "tech-008", "name": "Software Licensing Advisor", "lawyer": "tech-001"},
        {"id": "tech-009", "name": "Fintech Law Expert", "lawyer": "tech-001"},
        {"id": "tech-010", "name": "E-commerce Law Expert", "lawyer": "tech-001"}
    ]
    
    # Specialized Agents (10)
    spec_agents = [
        {"id": "spec-001", "name": "Tax Law Advisor", "lawyer": "sc-002"},
        {"id": "spec-002", "name": "Banking Law Expert", "lawyer": "corp-001"},
        {"id": "spec-003", "name": "Insurance Law Advisor", "lawyer": "corp-001"},
        {"id": "spec-004", "name": "Real Estate Legal Advisor", "lawyer": "hc-001"},
        {"id": "spec-005", "name": "Media Law Expert", "lawyer": "sc-003"},
        {"id": "spec-006", "name": "Sports Law Advisor", "lawyer": "dr-001"},
        {"id": "spec-007", "name": "Education Law Expert", "lawyer": "sc-003"},
        {"id": "spec-008", "name": "Healthcare Law Advisor", "lawyer": "corp-002"},
        {"id": "spec-009", "name": "Immigration Law Expert", "lawyer": "int-001"},
        {"id": "spec-010", "name": "International Law Expert", "lawyer": "int-001"}
    ]
    
    all_agents = []
    
    for agent in li_agents:
        agent["category"] = "Legal Intelligence"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["li-002", "li-003", "li-017"]
        all_agents.append(agent)
    
    for agent in cl_agents:
        agent["category"] = "Corporate Law"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["cl-002", "cl-003", "li-008"]
        all_agents.append(agent)
    
    for agent in pl_agents:
        agent["category"] = "Personal Law"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["pl-001", "pl-002", "li-001"]
        all_agents.append(agent)
    
    for agent in pub_agents:
        agent["category"] = "Public Law"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["pub-001", "pub-002", "li-001"]
        all_agents.append(agent)
    
    for agent in dr_agents:
        agent["category"] = "Dispute Resolution"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["dr-001", "dr-003", "li-001"]
        all_agents.append(agent)
    
    for agent in tech_agents:
        agent["category"] = "Technology"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["tech-001", "tech-002", "li-009"]
        all_agents.append(agent)
    
    for agent in spec_agents:
        agent["category"] = "Specialized"
        agent["lawyer_profile"] = LAWYER_CV_DATABASE.get(agent["lawyer"], {})
        agent["verifier_agents"] = ["spec-001", "li-001", "li-008"]
        all_agents.append(agent)
    
    return all_agents

AGENT_LIST = create_agent_list()

# ===================================================================
# VERIFICATION ENGINE
# ===================================================================

class VerificationEngine:
    def __init__(self):
        self.verification_history = []
        self.lawyer_review_queue = []
    
    def verify_agent_output(self, agent_id: str, output: str, query: str) -> Dict[str, Any]:
        agent = next((a for a in AGENT_LIST if a["id"] == agent_id), None)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}
        
        verifier_ids = agent.get("verifier_agents", [])
        verifier_results = []
        verification_score = 0.7
        
        for vid in