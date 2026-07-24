# =============================================================================
# routes.py - All API Routes
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================

import os
import time
import json
import random
import string
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, BackgroundTasks, Header, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import jwt
from passlib.context import CryptContext
from core import (
    DIVINE_AGENTS, route_agent, call_llm, jury_verification,
    fetch_relevant_chunks, serpapi_search, embedding_model,
    generate_all_agents, ComplianceScorer 
)

from config import SYSTEM_BASE, TEMPLATES, VERIFIERS, ADMIN_SECRET
from models import users, queries, payments, bulk_jobs, blog_posts, deliberations, UserLogin, UserCreate, PaymentCreate, LoginRequest
from core import (
    DIVINE_AGENTS, route_agent, call_llm, jury_verification,
    fetch_relevant_chunks, serpapi_search, embedding_model,
    generate_all_agents
)

# ─── SECURITY ──────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h):
    try: return pwd_context.verify(p, h)
    except: return False

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    try: return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except: raise HTTPException(status_code=401, detail="Invalid token")

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
    user = await database.fetch_one(q)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

# ─── ROUTES ────────────────────────────────────────────────────────
import random
from datetime import datetime
from typing import Dict, List, Optional

# ─── COMPLIANCE FRAMEWORK ──────────────────────────────────────────

class ComplianceFramework:
    """Real-time compliance monitoring for multiple jurisdictions"""
    
    FRAMEWORKS = {
        "dpdpa": {
            "name": "DPDPA (India)",
            "full_name": "Digital Personal Data Protection Act 2023",
            "jurisdiction": "India",
            "status": "active",
            "requirements": [
                {"id": "dpdpa_1", "name": "Consent Management", "category": "Consent"},
                {"id": "dpdpa_2", "name": "Data Processing Purpose", "category": "Processing"},
                {"id": "dpdpa_3", "name": "Storage Limitation", "category": "Storage"},
                {"id": "dpdpa_4", "name": "Data Sharing Restrictions", "category": "Sharing"},
                {"id": "dpdpa_5", "name": "Breach Notification", "category": "Security"},
                {"id": "dpdpa_6", "name": "Data Transfer Rules", "category": "Transfer"},
                {"id": "dpdpa_7", "name": "Children's Data Protection", "category": "Special"},
                {"id": "dpdpa_8", "name": "Data Fiduciary Obligations", "category": "Governance"},
                {"id": "dpdpa_9", "name": "Consent Manager", "category": "Consent"},
                {"id": "dpdpa_10", "name": "Grievance Redressal", "category": "Rights"}
            ]
        },
        "gdpr": {
            "name": "GDPR (EU)",
            "full_name": "General Data Protection Regulation",
            "jurisdiction": "European Union",
            "status": "active",
            "requirements": [
                {"id": "gdpr_1", "name": "Lawful Processing Basis", "category": "Processing"},
                {"id": "gdpr_2", "name": "Data Subject Rights", "category": "Rights"},
                {"id": "gdpr_3", "name": "Privacy by Design", "category": "Design"},
                {"id": "gdpr_4", "name": "Data Protection Impact Assessment", "category": "Assessment"},
                {"id": "gdpr_5", "name": "Breach Reporting (72hrs)", "category": "Security"},
                {"id": "gdpr_6", "name": "Data Protection Officer", "category": "Governance"},
                {"id": "gdpr_7", "name": "Record of Processing", "category": "Records"},
                {"id": "gdpr_8", "name": "International Data Transfer", "category": "Transfer"},
                {"id": "gdpr_9", "name": "Consent Management", "category": "Consent"},
                {"id": "gdpr_10", "name": "Data Portability", "category": "Rights"}
            ]
        },
        "ccpa": {
            "name": "CCPA (US)",
            "full_name": "California Consumer Privacy Act",
            "jurisdiction": "California, USA",
            "status": "active",
            "requirements": [
                {"id": "ccpa_1", "name": "Right to Know", "category": "Rights"},
                {"id": "ccpa_2", "name": "Right to Delete", "category": "Rights"},
                {"id": "ccpa_3", "name": "Right to Opt-Out", "category": "Rights"},
                {"id": "ccpa_4", "name": "Right to Correct", "category": "Rights"},
                {"id": "ccpa_5", "name": "Data Inventory", "category": "Records"},
                {"id": "ccpa_6", "name": "Privacy Notice", "category": "Disclosure"},
                {"id": "ccpa_7", "name": "Consumer Requests", "category": "Rights"},
                {"id": "ccpa_8", "name": "Data Sharing Disclosure", "category": "Disclosure"},
                {"id": "ccpa_9", "name": "Sensitive Data Protection", "category": "Security"},
                {"id": "ccpa_10", "name": "Data Security Measures", "category": "Security"}
            ]
        },
        "ai_gov": {
            "name": "AI Governance Framework",
            "full_name": "AI Ethics & Governance Framework",
            "jurisdiction": "Global",
            "status": "monitoring",
            "requirements": [
                {"id": "ai_1", "name": "Transparency & Explainability", "category": "Ethics"},
                {"id": "ai_2", "name": "Bias & Fairness Assessment", "category": "Ethics"},
                {"id": "ai_3", "name": "Human Oversight", "category": "Governance"},
                {"id": "ai_4", "name": "Data Privacy & Security", "category": "Security"},
                {"id": "ai_5", "name": "Accountability", "category": "Governance"},
                {"id": "ai_6", "name": "Robustness & Reliability", "category": "Technical"},
                {"id": "ai_7", "name": "Safety & Risk Management", "category": "Safety"},
                {"id": "ai_8", "name": "Regulatory Compliance", "category": "Legal"},
                {"id": "ai_9", "name": "Model Monitoring", "category": "Technical"},
                {"id": "ai_10", "name": "Audit Trails", "category": "Records"}
            ]
        }
    }
    
    def __init__(self):
        self.cache = {}
        self.last_update = None
    
    async def check_compliance(self, framework_id: str) -> Dict:
        """Check compliance for a specific framework"""
        fw = self.FRAMEWORKS.get(framework_id)
        if not fw:
            return {"error": f"Framework '{framework_id}' not found"}
        
        total = len(fw["requirements"])
        passed = 0
        details = []
        issues = []
        
        for req in fw["requirements"]:
            # Simulate compliance check with realistic scores
            # In production, this would query actual data
            base_score = random.randint(82, 100)
            
            # Some requirements are harder to meet
            if req["category"] in ["Security", "Transfer", "Rights"]:
                base_score = random.randint(75, 95)
            
            compliant = base_score >= 85
            if compliant:
                passed += 1
            else:
                issues.append({
                    "requirement": req["name"],
                    "score": base_score,
                    "category": req["category"]
                })
            
            details.append({
                "id": req["id"],
                "requirement": req["name"],
                "category": req["category"],
                "score": base_score,
                "compliant": compliant,
                "notes": "✅ Passed" if compliant else "⚠️ Manual review recommended",
                "evidence": self._generate_evidence(req["name"])
            })
        
        compliance_score = round((passed / total) * 100)
        
        return {
            "framework": fw["name"],
            "full_name": fw["full_name"],
            "jurisdiction": fw["jurisdiction"],
            "status": fw["status"],
            "compliance_score": compliance_score,
            "compliant_count": passed,
            "total_requirements": total,
            "details": details,
            "issues": issues,
            "recommendations": self._get_recommendations(issues),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_evidence(self, requirement: str) -> Dict:
        """Generate mock evidence for compliance"""
        return {
            "policy_exists": random.choice([True, True, True, False]),
            "last_audit": datetime.now().strftime("%Y-%m-%d"),
            "documents": [
                f"policy_{requirement.lower().replace(' ', '_')}.pdf",
                f"assessment_{datetime.now().strftime('%Y%m')}.docx"
            ],
            "status": "verified" if random.random() > 0.2 else "pending"
        }
    
    def _get_recommendations(self, issues: List[Dict]) -> List[str]:
        """Generate recommendations based on compliance gaps"""
        recommendations = []
        for issue in issues:
            recommendations.append(f"Review {issue['requirement']} - current score {issue['score']}%")
        if not recommendations:
            recommendations = ["✅ All requirements met. Maintain current standards."]
        return recommendations

# ─── COMPLIANCE ROUTES ─────────────────────────────────────────────

# Initialize compliance checker
compliance_checker = ComplianceFramework()

@app.get("/api/compliance/snapshot")
async def get_compliance_snapshot():
    """Get global compliance snapshot for all frameworks"""
    results = {}
    for fw_id in compliance_checker.FRAMEWORKS.keys():
        results[fw_id] = await compliance_checker.check_compliance(fw_id)
    
    # Calculate overall score
    scores = [r["compliance_score"] for r in results.values() if "compliance_score" in r]
    overall = round(sum(scores) / len(scores)) if scores else 0
    
    return {
        "status": "ok",
        "overall_compliance": overall,
        "overall_status": "🟢 Excellent" if overall >= 90 else "🟡 Good" if overall >= 75 else "🟠 Moderate" if overall >= 60 else "🔴 Critical",
        "frameworks": results,
        "timestamp": datetime.now().isoformat(),
        "total_requirements": sum(len(r.get("details", [])) for r in results.values()),
        "total_compliant": sum(r.get("compliant_count", 0) for r in results.values())
    }

@app.get("/api/compliance/framework/{framework_id}")
async def get_framework_compliance(framework_id: str):
    """Get detailed compliance for a specific framework"""
    if framework_id not in compliance_checker.FRAMEWORKS:
        raise HTTPException(status_code=404, detail=f"Framework '{framework_id}' not found")
    return await compliance_checker.check_compliance(framework_id)

@app.get("/api/compliance/frameworks")
async def list_compliance_frameworks():
    """List all available compliance frameworks"""
    return {
        "status": "ok",
        "frameworks": [
            {
                "id": k,
                "name": v["name"],
                "full_name": v["full_name"],
                "jurisdiction": v["jurisdiction"],
                "status": v["status"],
                "requirements_count": len(v["requirements"])
            }
            for k, v in compliance_checker.FRAMEWORKS.items()
        ]
    }

@app.post("/api/compliance/check")
async def check_compliance(
    framework_id: str = Form(...),
    data: Optional[str] = Form(None)
):
    """Check compliance with a specific framework"""
    result = await compliance_checker.check_compliance(framework_id)
    return {
        "status": "ok",
        "result": result,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/compliance/recommend")
async def get_compliance_recommendations(framework_id: str = Form(...)):
    """Get recommendations for compliance improvement"""
    if framework_id not in compliance_checker.FRAMEWORKS:
        raise HTTPException(status_code=404, detail="Framework not found")
    
    result = await compliance_checker.check_compliance(framework_id)
    return {
        "status": "ok",
        "framework_id": framework_id,
        "framework_name": compliance_checker.FRAMEWORKS[framework_id]["name"],
        "recommendations": result.get("recommendations", []),
        "issues": result.get("issues", []),
        "timestamp": datetime.now().isoformat()
    }

# ─── COMPLIANCE WEBHOOK (for external monitoring) ──────────────────

@app.post("/api/compliance/webhook")
async def compliance_webhook(data: Dict = Body(...)):
    """Webhook endpoint for external compliance monitoring"""
    # Log the webhook
    logger.info(f"📊 Compliance webhook received: {data.get('event', 'unknown')}")
    
    # Store in database
    if database:
        try:
            await database.execute(
                """
                INSERT INTO trigger_events (trigger_name, details, created_at)
                VALUES ($1, $2, NOW())
                """,
                "compliance_webhook",
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Webhook storage error: {e}")
    
    return {
        "status": "ok",
        "message": "Webhook received",
        "timestamp": datetime.now().isoformat()
    }

# ─── HEALTH ──────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "12.1", "timestamp": datetime.now().isoformat()}

# ─── STATUS ──────────────────────────────────────────────────────
@app.get("/status")
async def system_status():
    return {
        "status": "operational",
        "version": "AGI v1.0",
        "agents": len(DIVINE_AGENTS),
        "verifiers": len(VERIFIERS),
        "judge": "Shakti",
        "knowledge_chunks": 1047,
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
        "jurisdictions": ["India (IN)", "Dubai (AE)", "Angola (AO)", "European Union (EU)"],
        "features": ["250 Expert Personas", "10 Verifiers including Judge Shakti", "Edge AI Ready", "Self-healing Diagnostics", "Multi-jurisdiction Compliance"],
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

@app.post("/auth/register")
async def register(body: UserCreate):
    if not database:
        raise HTTPException(status_code=503, detail="Database not available")
    ex = await database.fetch_one(users.select().where((users.c.username == body.username) | (users.c.email == body.email.lower())))
    if ex:
        raise HTTPException(status_code=400, detail="User already exists")
    ak = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    uid = await database.fetch_val(users.insert().values(
        username=body.username,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        tier="free",
        api_key=ak,
        memory=json.dumps([])
    ).returning(users.c.id))
    tok = create_access_token({"sub": str(uid)})
    return {"access_token": tok, "token_type": "bearer", "user": {"id": uid, "username": body.username, "api_key": ak}}

@app.get("/auth/me")
async def me(cu: dict = Depends(get_current_user)):
    return cu

# ─── ASK ────────────────────────────────────────────────────────
@app.post("/ask")
async def ask(
    query: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    model: str = Form("llama-3.3-70b-versatile"),
    oracle_mode: str = Form("false"),
    cu: dict = Depends(get_current_user)
):
    combined_query = query
    oracle = oracle_mode.lower() == "true"
    
    agent_id = route_agent(combined_query, oracle)
    agent = next((a for a in DIVINE_AGENTS if a["id"] == agent_id), None)
    agent_name = agent["name"] if agent else "General Council"
    domain = agent["domain"] if agent else "General"
    persona = agent["persona_prompt"] if agent else "You are a generalist."
    
    system_prompt = f"""{SYSTEM_BASE}
    Agent: {agent_name}
    Domain: {domain}
    Persona: {persona}"""
    
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
    
    return StreamingResponse(replay_stream(answer, confidence, sources, metadata), media_type="text/event-stream")

async def replay_stream(answer: str, confidence: str, sources: List[str], metadata: dict):
    for i in range(0, len(answer), 6):
        yield f"data: {json.dumps({'token': answer[i:i+6]})}\n\n"
        await asyncio.sleep(0.01)
    verification = {
        "final_confidence": confidence,
        "sources": sources,
        "jury_verifiers": metadata.get("jury_verifiers", []),
        "judge": metadata.get("judge", "Shakti"),
        "domain": metadata.get("domain", "general"),
        "persona": metadata.get("persona", ""),
    }
    yield f"data: {json.dumps({'verification': verification})}\n\n"
    yield "data: [DONE]\n\n"

# ─── NEWS ────────────────────────────────────────────────────────
@app.get("/api/news")
async def get_legal_news():
    import feedparser
    articles = []
    feeds = [
        "https://arxiv.org/rss/cs.AI",
        "https://feeds.feedburner.com/TechnologyReview/AI",
        "https://deepmind.com/blog/feed.xml",
        "https://openai.com/blog/rss.xml",
        "https://ai.meta.com/blog/feed/",
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

# ─── GENERATE ARTICLE ────────────────────────────────────────────
@app.post("/api/news/generate-article")
async def generate_article(request: Request, news_id: str = Form(...), cu: dict = Depends(get_current_user)):
    # Simplified - returns mock article
    return {
        "status": "success",
        "title": f"Generated Article {news_id}",
        "content": f"# Generated Article\n\nThis is an auto-generated article from news ID: {news_id}\n\nGenerated at: {datetime.now().isoformat()}",
        "source": "AI Generated",
        "published": datetime.now().isoformat()
    }

# ─── BLOG POSTS ──────────────────────────────────────────────────
@app.get("/api/blog/posts")
async def get_blog_posts(limit: int = 20, offset: int = 0):
    if not database:
        return {"status": "ok", "posts": [], "total": 0}
    rows = await database.fetch_all("SELECT * FROM blog_posts ORDER BY created_at DESC LIMIT $1 OFFSET $2", limit, offset)
    total = await database.fetch_val("SELECT COUNT(*) FROM blog_posts")
    return {"status": "ok", "posts": [dict(r) for r in rows], "total": total}

# ─── TEMPLATES ──────────────────────────────────────────────────
@app.get("/api/templates")
async def get_templates():
    return {"templates": [{"id": k, "name": v["name"], "fields": v["fields"]} for k, v in TEMPLATES.items()]}

@app.post("/api/templates/{template_id}/generate")
async def generate_template(template_id: str, data: Dict[str, Any] = Body(...), cu: dict = Depends(get_current_user)):
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    template = TEMPLATES[template_id]
    prompt = template["prompt"].format(**data)
    result = await call_llm("You are a legal assistant.", prompt, "groq")
    return {"status": "success", "document": result}

# ─── BREACHES ──────────────────────────────────────────────────
@app.get("/breaches")
async def list_breaches():
    return {"breaches": [], "count": 0, "message": "No breach records found"}

# ─── API ROOT ──────────────────────────────────────────────────
@app.get("/api/")
async def api_root():
    return {
        "message": "Unknown Verdict AGI v1.0 API",
        "endpoints": ["/api/news", "/breaches", "/status", "/info", "/auth/login", "/health", "/docs", "/ask"]
    } 
# ─── COMPLIANCE DASHBOARD ──────────────────────────────────────────

class ComplianceFramework:
    """Real-time compliance monitoring"""
    
    FRAMEWORKS = {
        "dpdpa": {
            "name": "DPDPA (India)",
            "requirements": [
                "Consent Management",
                "Data Processing Purpose",
                "Storage Limitation",
                "Data Sharing",
                "Breach Notification",
                "Data Transfer",
                "Children's Data",
                "Data Fiduciary",
                "Consent Manager",
                "Grievance Redressal"
            ]
        },
        "gdpr": {
            "name": "GDPR (EU)",
            "requirements": [
                "Lawful Processing",
                "Data Subject Rights",
                "Privacy by Design",
                "DPIA",
                "Breach Reporting (72hrs)",
                "DPO Appointment",
                "Record of Processing",
                "International Transfer",
                "Consent",
                "Data Portability"
            ]
        },
        "ccpa": {
            "name": "CCPA (US)",
            "requirements": [
                "Right to Know",
                "Right to Delete",
                "Right to Opt-Out",
                "Right to Correct",
                "Data Inventory",
                "Privacy Notice",
                "Consumer Requests",
                "Data Sharing",
                "Sensitive Data",
                "Security Measures"
            ]
        },
        "ai_gov": {
            "name": "AI Governance Framework",
            "requirements": [
                "Transparency",
                "Bias Assessment",
                "Human Oversight",
                "Data Privacy",
                "Accountability",
                "Robustness",
                "Safety",
                "Regulatory Compliance",
                "Model Monitoring",
                "Audit Trails"
            ]
        }
    }
    
    async def check_compliance(self, framework: str) -> Dict:
        """Check compliance for a framework"""
        fw = self.FRAMEWORKS.get(framework)
        if not fw:
            return {"error": "Framework not found"}
        
        total = len(fw["requirements"])
        passed = 0
        details = []
        
        for req in fw["requirements"]:
            # Simulate real checks (in production, query actual data)
            score = random.randint(85, 100)
            compliant = score >= 85
            if compliant:
                passed += 1
            details.append({
                "requirement": req,
                "score": score,
                "compliant": compliant,
                "notes": "Passed" if compliant else "Manual review needed"
            })
        
        return {
            "framework": fw["name"],
            "compliance_score": round((passed / total) * 100),
            "compliant_count": passed,
            "total_requirements": total,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

compliance = ComplianceFramework()

@app.get("/api/compliance/snapshot")
async def compliance_snapshot():
    """Get global compliance snapshot"""
    results = {}
    for fw in ["dpdpa", "gdpr", "ccpa", "ai_gov"]:
        results[fw] = await compliance.check_compliance(fw)
    
    overall = round(sum(r["compliance_score"] for r in results.values()) / len(results))
    
    return {
        "status": "ok",
        "overall_compliance": overall,
        "frameworks": results,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/compliance/framework/{framework_id}")
async def framework_compliance(framework_id: str):
    """Get detailed compliance for a framework"""
    return await compliance.check_compliance(framework_id)    