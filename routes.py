# =============================================================================
# routes.py - All API Routes
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# =============================================================================

import os
import json
import random
import string
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import jwt
from passlib.context import CryptContext

from config import SYSTEM_BASE, TEMPLATES, VERIFIERS, ADMIN_SECRET
from models import users, UserLogin, UserCreate

# ─── IMPORT FROM CORE ──────────────────────────────────────────────
from core import (
    DIVINE_AGENTS,
    route_agent,
    call_llm,
    jury_verification,
    database,
    logger
)

# ─── SETUP LOGGER ──────────────────────────────────────────────────
if not logger:
    logger = logging.getLogger("unknown_verdict")

# ─── SECURITY ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

def hash_password(p):
    return pwd_context.hash(p)

def verify_password(p, h):
    try:
        return pwd_context.verify(p, h)
    except:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(cred.credentials)
    uid_or_username = payload.get("sub")
    if not uid_or_username:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        uid = int(uid_or_username)
        q = users.select().where(users.c.id == uid)
    except ValueError:
        q = users.select().where(users.c.username == uid_or_username)
    
    if not database:
        raise HTTPException(status_code=503, detail="Database not available")
    
    user = await database.fetch_one(q)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


# ═══════════════════════════════════════════════════════════════════════
# ✅ register_routes - THIS IS THE FUNCTION app.py CALLS
# ═══════════════════════════════════════════════════════════════════════

def register_routes(app: FastAPI):
    """Register all routes with the FastAPI app"""

    # ─── HEALTH ──────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": "12.1", "timestamp": datetime.now().isoformat()}

    # ─── STATUS ──────────────────────────────────────────────────────
    @app.get("/status")
    async def system_status():
        return {
            "status": "operational",
            "agents": len(DIVINE_AGENTS),
            "verifiers": len(VERIFIERS),
            "judge": "Shakti",
            "knowledge_chunks": 1047,
            "database": "connected" if database else "disconnected",
            "timestamp": datetime.now().isoformat()
        }

    # ─── INFO ────────────────────────────────────────────────────────
    @app.get("/info")
    async def system_info():
        return {
            "name": "Unknown Verdict AGI v1.0",
            "owner": "THE ADVOCACY - A LAW FIRM",
            "website": "www.advocacyalawfrim.in",
            "deployment": "Hugging Face Space: upamnyu12/LEX",
            "version": "v12.1"
        }

    # ─── AUTH LOGIN ──────────────────────────────────────────────────
    @app.post("/auth/login")
    async def login(body: UserLogin):
        if not database:
            raise HTTPException(status_code=503, detail="Database not available")
        u = await database.fetch_one(
            users.select().where(
                (users.c.username == body.username) | (users.c.email == body.username.lower())
            )
        )
        if not u or not verify_password(body.password, dict(u)["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        u = dict(u)
        tok = create_access_token({"sub": str(u["id"])})
        return {
            "access_token": tok,
            "token_type": "bearer",
            "user": {"id": u["id"], "username": u["username"], "email": u["email"], "tier": u["tier"]}
        }

    # ─── ASK ─────────────────────────────────────────────────────────
    @app.post("/ask")
    async def ask(
        query: str = Form(...),
        cu: dict = Depends(get_current_user)
    ):
        combined_query = query
        agent_id = route_agent(combined_query, False)
        agent = next((a for a in DIVINE_AGENTS if a["id"] == agent_id), None)
        agent_name = agent["name"] if agent else "General Council"
        domain = agent["domain"] if agent else "General"
        persona = agent["persona_prompt"] if agent else "You are a generalist."
        
        system_prompt = f"{SYSTEM_BASE}\nAgent: {agent_name}\nDomain: {domain}\nPersona: {persona}"
        
        initial_answer = await call_llm(system_prompt, combined_query, "groq")
        jury_result = await jury_verification(initial_answer, combined_query, domain)
        
        answer = jury_result["final_answer"]
        confidence = jury_result["confidence"]
        sources = jury_result["sources"]
        
        metadata = {
            "domain": domain,
            "persona": agent_name,
            "provider": "groq",
            "jury_verifiers": jury_result["jury_verifiers"],
            "judge": "Shakti"
        }
        
        async def replay_stream():
            for i in range(0, len(answer), 6):
                yield f"data: {json.dumps({'token': answer[i:i+6]})}\n\n"
                await asyncio.sleep(0.01)
            verification = {
                "final_confidence": confidence,
                "sources": sources,
                "jury_verifiers": metadata.get("jury_verifiers", []),
                "judge": metadata.get("judge", "Shakti")
            }
            yield f"data: {json.dumps({'verification': verification})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(replay_stream(), media_type="text/event-stream")

    # ─── NEWS ─────────────────────────────────────────────────────────
    @app.get("/api/news")
    async def get_legal_news():
        import feedparser
        articles = []
        feeds = [
            "https://arxiv.org/rss/cs.AI",
            "https://openai.com/blog/rss.xml",
        ]
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:3]:
                    articles.append({
                        "id": hashlib.md5(entry.title.encode()).hexdigest()[:8],
                        "title": entry.title,
                        "summary": entry.get('summary', '')[:300],
                        "link": entry.get('link', '#'),
                        "source": feed_url.split('/')[2],
                        "published": entry.get('published', datetime.now().strftime('%Y-%m-%d')),
                    })
            except:
                pass
        return {"status": "ok", "count": len(articles), "articles": articles[:20], "last_updated": datetime.now().isoformat()}

    # ─── BLOG POSTS ──────────────────────────────────────────────────
    @app.get("/api/blog/posts")
    async def get_blog_posts(limit: int = 20, offset: int = 0):
        if not database:
            return {"status": "ok", "posts": [], "total": 0}
        try:
            rows = await database.fetch_all(
                "SELECT * FROM blog_posts ORDER BY created_at DESC LIMIT :limit OFFSET :offset",
                {"limit": limit, "offset": offset}
            )
            total = await database.fetch_val("SELECT COUNT(*) FROM blog_posts") or 0
            return {
                "status": "ok",
                "posts": [dict(r) for r in rows],
                "total": total
            }
        except Exception as e:
            return {"status": "error", "posts": [], "total": 0, "error": str(e)}

    # ─── API ROOT ────────────────────────────────────────────────────
    @app.get("/api/")
    async def api_root():
        return {
            "message": "Unknown Verdict AGI v1.0 API",
            "endpoints": ["/api/news", "/status", "/info", "/auth/login", "/health", "/ask"]
        }

    # ─── COMPLIANCE ──────────────────────────────────────────────────
    @app.get("/api/compliance/snapshot")
    async def get_compliance_snapshot():
        return {
            "status": "ok",
            "overall_compliance": 90,
            "frameworks": {
                "dpdpa": {"compliance_score": 96},
                "gdpr": {"compliance_score": 94},
                "ccpa": {"compliance_score": 92}
            },
            "timestamp": datetime.now().isoformat()
        }

    # ─── LENS AGENTS ──────────────────────────────────────────────────
    @app.get("/api/lens/agents")
    async def list_lens_agents():
        return {
            "status": "ok",
            "agents": [],
            "count": 0
        }

    # ─── TRADING ──────────────────────────────────────────────────────
    @app.get("/api/trading/indices")
    async def get_indices():
        return {
            "status": "ok",
            "indices": {
                "NIFTY 50": {"price": 24500.50, "change_percent": 0.49},
                "SENSEX": {"price": 81500.25, "change_percent": 0.31},
                "BTC/USD": {"price": 65000.00, "change_percent": -1.81}
            },
            "timestamp": datetime.now().isoformat()
        }

    # ─── TRENDS ────────────────────────────────────────────────────────
    @app.get("/api/trends/ai")
    async def get_ai_trends():
        return {
            "status": "ok",
            "trends": {
                "market_size": {"global": 1.8e12, "growth_rate": 37.3},
                "investment": {"2026": 280e9},
                "jobs": {"net": 350000}
            },
            "timestamp": datetime.now().isoformat()
        }

    # ─── SPORTS ────────────────────────────────────────────────────────
    @app.get("/api/sports/cricket")
    async def get_cricket_scores():
        return {
            "status": "ok",
            "matches": [
                {"match": "India vs Australia", "status": "Live", "score": "245/3 (42.3 overs)"}
            ],
            "timestamp": datetime.now().isoformat()
        }

    # ─── DATABASE HELPERS ──────────────────────────────────────────────
    
    async def _create_tables():
        if not database:
            return
        try:
            await database.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except:
            pass
        
        tables = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                is_premium BOOLEAN DEFAULT FALSE,
                tier VARCHAR(20) DEFAULT 'free',
                queries_used_today INTEGER DEFAULT 0,
                last_query_reset TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                api_key VARCHAR(64) UNIQUE,
                preferences JSONB,
                memory JSONB DEFAULT '[]'
            )""",
            """CREATE TABLE IF NOT EXISTS queries (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                query TEXT,
                response TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS blog_posts (
                id SERIAL PRIMARY KEY,
                title TEXT,
                content TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                published BOOLEAN DEFAULT TRUE
            )""",
            """CREATE TABLE IF NOT EXISTS deliberations (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                domain TEXT,
                persona TEXT,
                provider TEXT,
                initial_answer TEXT,
                verifier_results JSONB,
                final_answer TEXT,
                confidence TEXT,
                sources JSONB,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL,
                embedding vector(384) NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding 
                ON knowledge_chunks 
                USING hnsw (embedding vector_cosine_ops)"""
        ]
        
        for stmt in tables:
            try:
                await database.execute(stmt)
            except Exception as e:
                if logger:
                    logger.warning(f"Table creation warning: {e}")

    async def _ensure_test_user():
        if not database:
            return
        try:
            existing = await database.fetch_one(
                "SELECT id FROM users WHERE username = 'counsel'"
            )
            if not existing:
                await database.execute(
                    """INSERT INTO users (username, email, password_hash, full_name, tier, api_key, memory)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                    "counsel",
                    "counsel@advocacyalawfrim.in",
                    pwd_context.hash("Password123!"),
                    "Counsel User",
                    "enterprise",
                    "".join(random.choices(string.ascii_letters + string.digits, k=32)),
                    json.dumps([])
                )
                if logger:
                    logger.info("✅ Seeded test user 'counsel'.")
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create test user: {e}")

    # Make helpers available to app.py
    register_routes._create_tables = _create_tables
    register_routes._ensure_test_user = _ensure_test_user

# ============================================
# ADD THESE ENDPOINTS TO routes.py
# ============================================

@router.get("/api/trading/indices")
async def get_indices():
    """Get live trading indices"""
    try:
        # Return mock data for now (replace with real API calls)
        return [
            {"symbol": "NIFTY", "name": "NIFTY 50", "price": "₹24,500.50", "change": 0.49},
            {"symbol": "SENSEX", "name": "SENSEX", "price": "₹81,500.25", "change": 0.31},
            {"symbol": "BTC", "name": "BTC/USD", "price": "$65,000.00", "change": -1.81}
        ]
    except Exception as e:
        logger.error(f"Trading indices error: {e}")
        return {"error": str(e)}

@router.get("/api/compliance/snapshot")
async def get_compliance_snapshot():
    """Get compliance snapshot"""
    try:
        return {
            "frameworks": [
                {"name": "GDPR", "score": 85, "status": "Compliant"},
                {"name": "DPDPA", "score": 70, "status": "In Progress"},
                {"name": "CCPA", "score": 90, "status": "Compliant"}
            ]
        }
    except Exception as e:
        logger.error(f"Compliance snapshot error: {e}")
        return {"error": str(e)}

@router.get("/api/trends/ai")
async def get_ai_trends():
    """Get AI industry trends"""
    try:
        return {
            "trends": [
                {"title": "Market Size", "value": "$150B", "description": "2024 Global AI Market"},
                {"title": "Investment", "value": "$25B", "description": "2024 AI Investment"},
                {"title": "Jobs", "value": "1.2M", "description": "AI Jobs Worldwide"}
            ]
        }
    except Exception as e:
        logger.error(f"Trends error: {e}")
        return {"error": str(e)}

@router.get("/api/news")
async def get_news(limit: int = 6):
    """Get legal news"""
    try:
        return {
            "articles": [
                {"title": "AI Regulation Update", "summary": "New EU AI Act provisions take effect", "source": "Legal Tech"},
                {"title": "DPDPA Implementation", "summary": "India's digital privacy law enters phase 2", "source": "Indian Law"},
                {"title": "Blockchain Legal Framework", "summary": "New guidelines for crypto assets", "source": "FinTech Law"}
            ]
        }
    except Exception as e:
        logger.error(f"News error: {e}")
        return {"error": str(e)}

@router.get("/api/lens/agents")
async def get_lens_agents():
    """Get lens agents status"""
    try:
        return {
            "status": "active",
            "total_agents": 250,
            "active_agents": 248,
            "domains": ["Legal", "Tech", "Markets", "Compliance"]
        }
    except Exception as e:
        logger.error(f"Lens agents error: {e}")
        return {"error": str(e)}    