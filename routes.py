# ============================================
# ROUTES.PY - WITH CORRECT IMPORTS
# ============================================

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from typing import Optional, List, Dict, Any
import json
import os
import logging
from datetime import datetime, timedelta
import asyncio
import asyncpg

# CREATE ROUTER
router = APIRouter()

# Set up logger
logger = logging.getLogger("unknown_verdict")

# IMPORT MODELS - USE CORRECT NAMES
from models import (
    User, Session, LegalDocument, ChatHistory, 
    ComplianceRecord, TradeData, NewsArticle, LensScan
)
from core import UnknownVerdictEngine, get_engine
from config import DATABASE_URL, JWT_SECRET, REDIS_URL

# ============================================
# SIMPLIFIED DATABASE INIT (without SQLAlchemy)
# ============================================

async def _create_tables():
    """Create tables using raw SQL (most reliable)"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sessions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Chat history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                session_id VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                response TEXT,
                agent_name VARCHAR(100),
                verifier_score FLOAT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Legal documents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS legal_documents (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                content TEXT,
                category VARCHAR(100),
                jurisdiction VARCHAR(100),
                document_type VARCHAR(50),
                metadata JSONB,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Compliance records table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS compliance_records (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                framework VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                score INTEGER,
                details JSONB,
                recommendations JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trade data table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                price FLOAT NOT NULL,
                change FLOAT,
                change_percent FLOAT,
                volume FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source VARCHAR(50)
            )
        """)
        
        # News articles table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                summary TEXT,
                content TEXT,
                source VARCHAR(100),
                url VARCHAR(500),
                category VARCHAR(50),
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Lens scans table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lens_scans (
                id SERIAL PRIMARY KEY,
                domain VARCHAR(100) NOT NULL,
                agent_name VARCHAR(100) NOT NULL,
                status VARCHAR(50) DEFAULT 'active',
                results JSONB,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.close()
        logger.info("✅ All tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Table creation failed: {e}")
        return False

async def init_database():
    """Initialize database"""
    try:
        if not DATABASE_URL:
            logger.warning("⚠️ No DATABASE_URL, skipping initialization")
            return False
        
        success = await _create_tables()
        if success:
            logger.info("✅ Database initialized successfully")
            return True
        else:
            logger.warning("⚠️ Database initialization failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")
        return False

# ============================================
# AUTHENTICATION FUNCTIONS
# ============================================

from passlib.context import CryptContext
import jwt
import hashlib
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

# ============================================
# API ENDPOINTS (Simplified - No ORM)
# ============================================

@router.get("/")
async def root():
    """Serve frontend"""
    return FileResponse("static/index.html")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "12.1", "database": "postgresql"}

# ============================================
# AUTH ENDPOINTS
# ============================================

@router.post("/api/register")
async def register_user(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        
        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check existing
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1 OR email = $2", 
            username, email
        )
        if existing:
            await conn.close()
            raise HTTPException(status_code=400, detail="Username or email already registered")
        
        # Insert
        hashed = get_password_hash(password)
        result = await conn.fetchrow(
            "INSERT INTO users (username, email, hashed_password, full_name) VALUES ($1, $2, $3, $4) RETURNING id",
            username, email, hashed, full_name
        )
        
        await conn.close()
        
        return {
            "status": "success",
            "message": "User registered successfully",
            "user_id": result["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/login")
async def login_user(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing credentials")
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        user = await conn.fetchrow(
            "SELECT id, username, email, hashed_password FROM users WHERE username = $1 OR email = $1",
            username
        )
        
        if not user:
            await conn.close()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not verify_password(password, user["hashed_password"]):
            await conn.close()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create token
        token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
        
        # Store session
        await conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES ($1, $2, $3)",
            user["id"], token, datetime.utcnow() + timedelta(days=7)
        )
        
        await conn.close()
        
        return {
            "status": "success",
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CHAT ENDPOINT
# ============================================

@router.post("/api/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id", "default")
        
        if not message:
            return JSONResponse({"error": "Message is required"}, status_code=400)
        
        # Get engine
        engine = get_engine()
        
        # Process
        response = await engine.process_message(message, session_id)
        
        # Store in DB
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "INSERT INTO chat_history (session_id, message, response, agent_name) VALUES ($1, $2, $3, $4)",
                session_id, message, response.get("response", ""), response.get("agent", "Unknown")
            )
            await conn.close()
        except:
            pass  # Continue even if DB fails
        
        return {
            "response": response.get("response", "I've processed your legal query. How can I further assist?"),
            "session_id": session_id,
            "agent_used": response.get("agent", "Legal Counsel")
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================
# DATA ENDPOINTS
# ============================================

@router.get("/api/trading/indices")
async def get_indices():
    return [
        {"symbol": "NIFTY", "name": "NIFTY 50", "price": "₹24,500.50", "change": 0.49},
        {"symbol": "SENSEX", "name": "SENSEX", "price": "₹81,500.25", "change": 0.31},
        {"symbol": "BTC", "name": "BTC/USD", "price": "$65,000.00", "change": -1.81}
    ]

@router.get("/api/compliance/snapshot")
async def get_compliance_snapshot():
    return {
        "frameworks": [
            {"name": "GDPR", "score": 85, "status": "Compliant"},
            {"name": "DPDPA", "score": 70, "status": "In Progress"},
            {"name": "CCPA", "score": 90, "status": "Compliant"}
        ]
    }

@router.get("/api/trends/ai")
async def get_ai_trends():
    return {
        "trends": [
            {"title": "Market Size", "value": "$150B", "description": "2024 Global AI Market"},
            {"title": "Investment", "value": "$25B", "description": "2024 AI Investment"},
            {"title": "Jobs", "value": "1.2M", "description": "AI Jobs Worldwide"}
        ]
    }

@router.get("/api/news")
async def get_news(limit: int = 6):
    news_items = [
        {"title": "AI Regulation Update", "summary": "New EU AI Act provisions take effect", "source": "Legal Tech"},
        {"title": "DPDPA Implementation", "summary": "India's digital privacy law enters phase 2", "source": "Indian Law"},
        {"title": "Blockchain Legal Framework", "summary": "New guidelines for crypto assets", "source": "FinTech Law"},
        {"title": "Supreme Court AI Ruling", "summary": "Landmark case on AI liability", "source": "Supreme Court"},
        {"title": "Data Protection Bill", "summary": "New amendments proposed", "source": "Parliament"},
        {"title": "Legal Tech Investment", "summary": "$500M raised in Q2 2024", "source": "TechCrunch"}
    ]
    return {"articles": news_items[:limit]}

@router.get("/api/lens/agents")
async def get_lens_agents():
    return {
        "status": "active",
        "total_agents": 250,
        "active_agents": 248,
        "domains": ["Legal", "Tech", "Markets", "Compliance", "Spiritual", "Scientific"]
    }

# ============================================
# EXPOSE ROUTER
# ============================================

__all__ = ['router', 'init_database']