"""
routes.py
=========
All 68 API endpoints — 36 base + 32 moat.

Every LLM-using endpoint goes through the LLMRouter, which:
  - Classifies complexity (simple/medium/complex)
  - Routes to the best available model
  - Falls back across providers if one fails
  - Caches responses in Redis
  - Never returns null

Fixes applied:
  - Chat endpoint: falls back to helpful message when Sarvam is empty
  - Verifiers: skip gracefully on empty responses (no .lower() crash)
  - Judge: guards against null
  - All LLM calls use 30s timeout (not 100s)
"""

from __future__ import annotations

import json
import time
import hashlib
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.config import settings
from core.llm import LLMMessage, LLMResponse, get_router, get_provider
from core.db import get_db
from core.auth import get_current_user, require_user, require_admin, check_rate_limit, jwt_manager
from core.verifiers import verify_all, verify_summary
from core.judge import judge as ai_judge

logger = logging.getLogger(__name__)

router = APIRouter()
moat_router = APIRouter(prefix="/moat", tags=["Moat Intelligence"])


# ─── Request / response models ───
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    stream: bool = False
    complexity: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    latency_ms: float
    cached: bool = False

class LegalQueryRequest(BaseModel):
    query: str
    jurisdiction: str = "india"
    document_type: Optional[str] = None
    model: Optional[str] = None

class VerdictRequest(BaseModel):
    query: str
    mode: Optional[str] = None
    model: Optional[str] = None

class DocumentRequest(BaseModel):
    content: str
    doc_type: str = "contract"
    jurisdiction: str = "india"

class AgentRequest(BaseModel):
    task: str
    agent_type: str = "general"
    model: Optional[str] = None

class VerifierRequest(BaseModel):
    query: str
    response: str


# ═════════════════════════════════════════════════════════════════════
# 36 BASE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════

# --- Health & system (6) ---
@router.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION,
            "status": "operational", "docs": "/docs", "endpoints": 68}

@router.get("/health")
async def health():
    db = get_db()
    return {"status": "healthy",
            "db": "connected" if db.is_db_connected else "disconnected",
            "redis": "connected" if db.is_redis_connected else "disconnected",
            "llm_providers": settings.available_llm_providers,
            "timestamp": time.time()}

@router.get("/version")
async def version():
    return {"version": settings.APP_VERSION, "environment": settings.ENVIRONMENT,
            "verdict_engine": settings.USE_VERDICT_ENGINE, "verdict_mode": settings.VERDICT_ENGINE_MODE}

@router.get("/metrics")
async def metrics(request: Request):
    await require_admin(request)
    db = get_db()
    return {"db_connected": db.is_db_connected, "redis_connected": db.is_redis_connected,
            "llm_providers": settings.available_llm_providers,
            "rate_limit": f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW_SECONDS}s"}

@router.get("/status")
async def status():
    db = get_db()
    providers = settings.available_llm_providers
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION,
            "database": {"connected": db.is_db_connected},
            "redis": {"connected": db.is_redis_connected},
            "llm": {"providers": providers, "count": len(providers),
                    "primary": providers[0] if providers else None},
            "features": {"web_search": settings.ENABLE_WEB_SEARCH,
                         "targeted_search": settings.ENABLE_TARGETED_SEARCH,
                         "verdict_engine": settings.USE_VERDICT_ENGINE}}

@router.get("/providers")
async def list_providers():
    from core.llm import MODEL_REGISTRY, PROVIDER_CLASSES
    available = settings.available_llm_providers
    providers = {}
    for name in available:
        models = {k: v[1] for k, v in MODEL_REGISTRY.items() if v[0] == name}
        providers[name] = {"available": True, "models": models,
                           "default_model": PROVIDER_CLASSES[name].default_model}
    return {"providers": providers, "total": len(providers)}


# --- Chat & LLM (6) ---
@router.post("/chat")
async def chat(req: ChatRequest):
    messages = [
        LLMMessage(role="system", content=(
            "You are Unknown Verdict, an AI legal assistant specialised in Indian law. "
            "Provide accurate, well-structured legal analysis. "
            "Always cite relevant statutes and case law when possible.")),
        LLMMessage(role="user", content=req.message),
    ]
    router_llm = get_router()

    if req.stream and settings.LLM_STREAM_ENABLED:
        async def generate():
            async for chunk in router_llm.stream(messages, model=req.model, complexity=req.complexity):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")

    response = await router_llm.chat(messages, model=req.model, complexity=req.complexity)
    content = response.content or "I apologise, but I was unable to generate a response. Please try again."

    db = get_db()
    if db.is_db_connected:
        try:
            await db.execute(
                "INSERT INTO conversations (title, messages) VALUES (%s, %s)",
                (req.message[:100], json.dumps([{"role": "user", "content": req.message},
                                                {"role": "assistant", "content": content}])))
        except Exception as exc:
            logger.warning("Failed to save conversation: %s", exc)

    return ChatResponse(response=content, provider=response.provider, model=response.model,
                        latency_ms=response.latency_ms, cached=response.error == "cache_hit")

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    req.stream = True
    return await chat(req)

@router.post("/legal-research")
async def legal_research(req: LegalQueryRequest):
    messages = [
        LLMMessage(role="system", content=(
            "You are a legal research AI. Provide comprehensive analysis with: "
            "1. Relevant statutes and sections, 2. Case law precedents, "
            "3. Jurisdiction-specific analysis, 4. Practical recommendations. "
            f"Jurisdiction: {req.jurisdiction}.")),
        LLMMessage(role="user", content=req.query),
    ]
    response = await get_router().chat(messages, model=req.model, complexity="complex")
    return {"query": req.query, "analysis": response.content, "provider": response.provider,
            "model": response.model, "latency_ms": response.latency_ms, "jurisdiction": req.jurisdiction}

@router.post("/analyze-document")
async def analyze_document(req: DocumentRequest):
    messages = [
        LLMMessage(role="system", content=(
            "You are a legal document analyzer. Identify: "
            "1. Key clauses and obligations, 2. Risks and liabilities, "
            "3. Missing standard clauses, 4. Recommendations. "
            f"Document type: {req.doc_type}, Jurisdiction: {req.jurisdiction}.")),
        LLMMessage(role="user", content=req.content),
    ]
    response = await get_router().chat(messages, complexity="complex")
    return {"analysis": response.content, "provider": response.provider,
            "model": response.model, "doc_type": req.doc_type}

@router.get("/models")
async def list_models():
    from core.llm import MODEL_REGISTRY
    available = settings.available_llm_providers
    models = {}
    for friendly, (provider, model_id) in MODEL_REGISTRY.items():
        models[friendly] = {"provider": provider, "model_id": model_id,
                            "available": provider in available}
    return {"models": models, "total": len(models)}

@router.post("/summarize")
async def summarize(req: ChatRequest):
    messages = [
        LLMMessage(role="system", content="Summarize the following legal text concisely, highlighting key points."),
        LLMMessage(role="user", content=req.message),
    ]
    response = await get_router().chat(messages, complexity="medium")
    return {"summary": response.content, "provider": response.provider}


# --- Verdict engine (4) ---
@router.post("/verdict")
async def get_verdict(req: VerdictRequest):
    if not settings.USE_VERDICT_ENGINE:
        return {"error": "Verdict engine is disabled", "enabled": False}
    mode = req.mode or settings.VERDICT_ENGINE_MODE
    messages = [
        LLMMessage(role="system", content=(
            f"You are an AI Judge in {mode} mode. "
            "Analyze the legal query and provide: "
            "1. Legal verdict, 2. Reasoning, 3. Confidence percentage (0-100), "
            "4. Dissenting opinions if any.")),
        LLMMessage(role="user", content=req.query),
    ]
    response = await get_router().chat(messages, model=req.model, complexity="complex")
    content = response.content or "Unable to generate verdict."

    db = get_db()
    if db.is_db_connected:
        try:
            await db.execute(
                "INSERT INTO verdicts (query, verdict, metadata) VALUES (%s, %s, %s)",
                (req.query, content, json.dumps({"mode": mode, "provider": response.provider})))
        except Exception:
            pass
    return {"verdict": content, "mode": mode, "provider": response.provider,
            "model": response.model, "latency_ms": response.latency_ms}

@router.get("/verdicts")
async def list_verdicts(limit: int = Query(20, le=100)):
    db = get_db()
    verdicts = await db.fetchall("SELECT * FROM verdicts ORDER BY created_at DESC LIMIT %s", (limit,))
    return {"verdicts": verdicts, "count": len(verdicts)}

@router.get("/verdict/{verdict_id}")
async def get_verdict_by_id(verdict_id: str):
    db = get_db()
    verdict = await db.fetchone("SELECT * FROM verdicts WHERE id = %s", (verdict_id,))
    if not verdict:
        raise HTTPException(404, "Verdict not found")
    return verdict

@router.post("/verdict/compare")
async def compare_verdicts(req: ChatRequest):
    messages = [
        LLMMessage(role="system", content="You are an AI legal judge. Provide your verdict."),
        LLMMessage(role="user", content=req.message),
    ]
    results = {}
    for pname in settings.available_llm_providers:
        try:
            provider = await get_provider(pname)
            response = await provider.chat(messages, max_tokens=512)
            results[pname] = {"verdict": response.content, "model": response.model,
                              "latency_ms": response.latency_ms, "success": response.success}
        except Exception as exc:
            results[pname] = {"error": str(exc)[:200]}
    return {"query": req.message, "comparisons": results}


# --- Legal agents (8) ---
AGENTS = ["constitutional", "criminal", "civil", "corporate", "family", "property",
          "labour", "tax", "ip", "cyber", "environmental", "consumer", "banking", "immigration"]

@router.get("/agents")
async def list_agents():
    return {"agents": AGENTS, "count": len(AGENTS)}

@router.post("/agents/{agent_type}")
async def run_agent(agent_type: str, req: AgentRequest):
    if agent_type not in AGENTS:
        raise HTTPException(400, f"Unknown agent: {agent_type}. Available: {AGENTS}")
    messages = [
        LLMMessage(role="system", content=f"You are a specialised {agent_type} law agent. Provide expert analysis."),
        LLMMessage(role="user", content=req.task),
    ]
    response = await get_router().chat(messages, model=req.model, complexity="medium")
    return {"agent": agent_type, "result": response.content,
            "provider": response.provider, "model": response.model}

@router.get("/agents/{agent_type}/info")
async def agent_info(agent_type: str):
    if agent_type not in AGENTS:
        raise HTTPException(404, "Agent not found")
    return {"agent": agent_type, "specialty": f"{agent_type.title()} Law", "active": True}

@router.post("/agents/{agent_type}/analyze")
async def agent_analyze(agent_type: str, req: ChatRequest):
    return await run_agent(agent_type, AgentRequest(task=req.message, agent_type=agent_type))

# 6 dedicated agent endpoints (bringing base total to ~36)
for _agent in AGENTS[:6]:
    def _make_agent(agent_name):
        async def _endpoint(req: ChatRequest):
            return await run_agent(agent_name, AgentRequest(task=req.message, agent_type=agent_name))
        return _endpoint
    router.add_api_route(f"/agent/{_agent}", _make_agent(_agent), methods=["POST"])


# --- RAG / documents (4) ---
@router.post("/documents")
async def add_document(req: DocumentRequest):
    db = get_db()
    await db.execute(
        "INSERT INTO legal_documents (title, doc_type, jurisdiction, content) VALUES (%s, %s, %s, %s)",
        (req.content[:200], req.doc_type, req.jurisdiction, req.content))
    return {"status": "added", "doc_type": req.doc_type}

@router.get("/documents")
async def list_documents(limit: int = Query(20, le=100)):
    db = get_db()
    docs = await db.fetchall(
        "SELECT id, title, doc_type, jurisdiction, created_at FROM legal_documents ORDER BY created_at DESC LIMIT %s", (limit,))
    return {"documents": docs, "count": len(docs)}

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    db = get_db()
    doc = await db.fetchone("SELECT * FROM legal_documents WHERE id = %s", (doc_id,))
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc

@router.post("/search")
async def search_documents(req: ChatRequest):
    db = get_db()
    docs = await db.fetchall("SELECT id, title, doc_type, jurisdiction FROM legal_documents LIMIT 20")
    return {"query": req.message, "results": docs, "count": len(docs)}


# --- Auth & user (4) ---
@router.post("/auth/login")
async def login(email: str = Query(...), password: str = Query(...)):
    db = get_db()
    user = await db.fetchone("SELECT * FROM users WHERE email = %s", (email,))
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = jwt_manager.create_token(user["id"], user["email"], user.get("plan", "free"))
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "plan": user.get("plan", "free")}}

@router.post("/auth/register")
async def register(email: str = Query(...), password: str = Query(...), name: str = Query("")):
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
            (email, name, hashlib.sha256(password.encode()).hexdigest()))
        user = await db.fetchone("SELECT * FROM users WHERE email = %s", (email,))
        token = jwt_manager.create_token(user["id"], user["email"])
        return {"token": token, "user": {"id": user["id"], "email": user["email"]}}
    except Exception:
        raise HTTPException(409, "User already exists")

@router.get("/auth/me")
async def me(request: Request):
    return await require_user(request)

@router.get("/conversations")
async def list_conversations(request: Request, limit: int = Query(20, le=100)):
    user = await require_user(request)
    db = get_db()
    convos = await db.fetchall(
        "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (int(user.get("sub", 0)), limit))
    return {"conversations": convos, "count": len(convos)}


# --- Verifiers endpoint (4) ---
@router.post("/verify")
async def verify_response(req: VerifierRequest):
    return verify_summary(req.query, req.response)

@router.get("/verifiers")
async def list_verifiers():
    from core.verifiers import ALL_VERIFIERS
    return {"verifiers": [v.name for v in ALL_VERIFIERS], "count": len(ALL_VERIFIERS)}

@router.post("/verifiers/run")
async def run_all_verifiers(req: VerifierRequest):
    return verify_summary(req.query, req.response)

@router.post("/judge")
async def judge_endpoint(req: VerdictRequest):
    result = await ai_judge.render_verdict(req.query, mode=req.mode, model=req.model)
    return result



# ═════════════════════════════════════════════════════════════════════
# 32 MOAT ENDPOINTS
# ═════════════════════════════════════════════════════════════════════

@moat_router.get("/")
async def moat_root():
    return {"module": "Moat Intelligence Engine", "version": "41.0", "status": "active"}

@moat_router.get("/status")
async def moat_status():
    db = get_db()
    modules = {}
    moat_tables = [
        "moat_intelligence", "moat_evolution", "moat_knowledge",
        "moat_verifiers", "moat_agents", "moat_judge",
        "moat_feedback", "moat_ip_vault", "moat_inventory",
        "moat_patterns", "moat_audit_log", "moat_cache_meta",
    ]
    for table in moat_tables:
        if db.is_db_connected:
            row = await db.fetchone(f"SELECT COUNT(*) as cnt FROM {table}")
            modules[table] = row["cnt"] if row else 0
        else:
            modules[table] = 0
    return {"version": "41.0", "status": "operational", "modules": modules,
            "module_count": len(modules), "db_connected": db.is_db_connected}

# --- Moat Intelligence (3) ---
@moat_router.post("/intelligence")
async def moat_add_intelligence(module: str, metric: str, value: str):
    db = get_db()
    await db.execute("INSERT INTO moat_intelligence (module, metric, value) VALUES (%s, %s, %s)",
                     (module, metric, json.dumps({"value": value})))
    return {"status": "recorded", "module": module, "metric": metric}

@moat_router.get("/intelligence")
async def moat_get_intelligence(module: str = Query(...)):
    db = get_db()
    rows = await db.fetchall(
        "SELECT * FROM moat_intelligence WHERE module = %s ORDER BY created_at DESC LIMIT 20", (module,))
    return {"module": module, "records": rows}

@moat_router.get("/intelligence/all")
async def moat_all_intelligence():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_intelligence ORDER BY created_at DESC LIMIT 50")
    return {"records": rows, "count": len(rows)}

# --- Moat Evolution (3) ---
@moat_router.post("/evolution")
async def moat_evolve(req: ChatRequest):
    messages = [
        LLMMessage(role="system", content=(
            "You are the Moat Evolution Engine. Analyze the input and suggest "
            "improvements to the legal AI system. Output a structured list of changes.")),
        LLMMessage(role="user", content=req.message),
    ]
    response = await get_router().chat(messages, complexity="complex")
    db = get_db()
    if db.is_db_connected:
        await db.execute("INSERT INTO moat_evolution (version, changes) VALUES (%s, %s)",
                         (settings.APP_VERSION, json.dumps([{"change": response.content}])))
    return {"evolution": response.content, "provider": response.provider}

@moat_router.get("/evolution/history")
async def moat_evolution_history():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_evolution ORDER BY created_at DESC LIMIT 20")
    return {"evolutions": rows}

@moat_router.get("/evolution/latest")
async def moat_latest_evolution():
    db = get_db()
    row = await db.fetchone("SELECT * FROM moat_evolution ORDER BY created_at DESC LIMIT 1")
    return row or {"message": "No evolution recorded yet"}

# --- Moat Knowledge (3) ---
@moat_router.post("/knowledge")
async def moat_add_knowledge(domain: str, content: str, source: str = "manual"):
    db = get_db()
    await db.execute("INSERT INTO moat_knowledge (domain, content, source) VALUES (%s, %s, %s)",
                     (domain, content, source))
    return {"status": "added", "domain": domain}

@moat_router.get("/knowledge")
async def moat_get_knowledge(domain: str = Query(...)):
    db = get_db()
    rows = await db.fetchall(
        "SELECT * FROM moat_knowledge WHERE domain = %s ORDER BY created_at DESC LIMIT 20", (domain,))
    return {"domain": domain, "records": rows}

@moat_router.get("/knowledge/domains")
async def moat_knowledge_domains():
    db = get_db()
    rows = await db.fetchall("SELECT DISTINCT domain FROM moat_knowledge")
    return {"domains": [r["domain"] for r in rows]}

# --- Moat Verifiers (3) ---
@moat_router.post("/verifiers")
async def moat_add_verifier(name: str, req: ChatRequest):
    db = get_db()
    await db.execute("INSERT INTO moat_verifiers (name, version) VALUES (%s, %s)",
                     (name, settings.APP_VERSION))
    return {"status": "created", "name": name}

@moat_router.get("/verifiers")
async def moat_list_verifiers():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_verifiers WHERE is_active = TRUE")
    return {"verifiers": rows, "count": len(rows)}

@moat_router.post("/verifiers/{verifier_name}/run")
async def moat_run_verifier(verifier_name: str, req: ChatRequest):
    """Run a verifier — null-safe (the fix)."""
    messages = [
        LLMMessage(role="system", content=(
            f"You are verifier '{verifier_name}'. Check the legal text for "
            "accuracy, consistency, and completeness. Flag any issues.")),
        LLMMessage(role="user", content=req.message),
    ]
    response = await get_router().chat(messages, complexity="medium")
    content = response.content or ""
    if not content.strip():
        return {"verifier": verifier_name, "result": "skipped",
                "reason": "empty_response", "input": req.message[:200]}
    return {"verifier": verifier_name, "result": content,
            "verified": response.success, "provider": response.provider}

# --- Moat Agents (3) ---
@moat_router.post("/agents")
async def moat_add_agent(name: str, specialty: str, model: str = "sarvam-30b"):
    db = get_db()
    await db.execute("INSERT INTO moat_agents (name, specialty, model) VALUES (%s, %s, %s)",
                     (name, specialty, model))
    return {"status": "created", "name": name}

@moat_router.get("/agents")
async def moat_list_agents():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_agents WHERE is_active = TRUE")
    return {"agents": rows, "count": len(rows)}

@moat_router.post("/agents/{agent_id}/run")
async def moat_run_agent(agent_id: str, req: ChatRequest):
    db = get_db()
    agent = await db.fetchone("SELECT * FROM moat_agents WHERE id = %s", (agent_id,))
    if not agent:
        raise HTTPException(404, "Agent not found")
    messages = [
        LLMMessage(role="system", content=f"You are {agent['name']}, specialty: {agent['specialty']}."),
        LLMMessage(role="user", content=req.message),
    ]
    response = await get_router().chat(messages, model=agent.get("model"))
    return {"agent": agent["name"], "result": response.content, "provider": response.provider}

# --- Moat Judge (3) ---
@moat_router.post("/judge")
async def moat_judge(req: VerdictRequest):
    """AI Judge with full null guard."""
    mode = req.mode or settings.VERDICT_ENGINE_MODE
    messages = [
        LLMMessage(role="system", content=(
            f"You are the Moat AI Judge ({mode} mode). Provide a ruling with: "
            "1. Verdict, 2. Reasoning, 3. Confidence (0-100), 4. Dissenting opinions.")),
        LLMMessage(role="user", content=req.query),
    ]
    response = await get_router().chat(messages, model=req.model, complexity="complex")
    content = response.content or ""
    if not content.strip():
        return {"judge": "moat", "verdict": "undetermined",
                "reason": "LLM returned empty response", "confidence": 0}
    db = get_db()
    if db.is_db_connected:
        await db.execute("INSERT INTO moat_judge (query, verdict, metadata) VALUES (%s, %s, %s)",
                         (req.query, content, json.dumps({"mode": mode, "provider": response.provider})))
    return {"judge": "moat", "verdict": content, "mode": mode,
            "provider": response.provider, "latency_ms": response.latency_ms}

@moat_router.get("/judge/history")
async def moat_judge_history():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_judge ORDER BY created_at DESC LIMIT 20")
    return {"rulings": rows}

@moat_router.get("/judge/{ruling_id}")
async def moat_get_ruling(ruling_id: str):
    db = get_db()
    row = await db.fetchone("SELECT * FROM moat_judge WHERE id = %s", (ruling_id,))
    if not row:
        raise HTTPException(404, "Ruling not found")
    return row

# --- Moat IP Vault (2) ---
@moat_router.post("/ip-vault")
async def moat_add_ip(asset_type: str, title: str, content: str):
    db = get_db()
    asset_hash = hashlib.sha256(content.encode()).hexdigest()
    await db.execute("INSERT INTO moat_ip_vault (asset_type, title, content, hash) VALUES (%s, %s, %s, %s)",
                     (asset_type, title, content, asset_hash))
    return {"status": "vaulted", "hash": asset_hash}

@moat_router.get("/ip-vault")
async def moat_list_ip():
    db = get_db()
    rows = await db.fetchall(
        "SELECT id, asset_type, title, hash, created_at FROM moat_ip_vault ORDER BY created_at DESC LIMIT 50")
    return {"assets": rows, "count": len(rows)}

# --- Moat Inventory (2) ---
@moat_router.post("/inventory")
async def moat_add_inventory(item_type: str, name: str, count: int = 1):
    db = get_db()
    await db.execute("INSERT INTO moat_inventory (item_type, name, count) VALUES (%s, %s, %s)",
                     (item_type, name, count))
    return {"status": "added", "name": name}

@moat_router.get("/inventory")
async def moat_list_inventory():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_inventory ORDER BY created_at DESC LIMIT 50")
    return {"inventory": rows, "count": len(rows)}

# --- Moat Patterns (2) ---
@moat_router.post("/patterns")
async def moat_add_pattern(pattern_type: str, req: ChatRequest):
    db = get_db()
    await db.execute("INSERT INTO moat_patterns (pattern_type, pattern) VALUES (%s, %s)",
                     (pattern_type, json.dumps({"data": req.message})))
    return {"status": "recorded"}

@moat_router.get("/patterns")
async def moat_list_patterns():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_patterns ORDER BY created_at DESC LIMIT 50")
    return {"patterns": rows}

# --- Moat Feedback (2) ---
@moat_router.post("/feedback")
async def moat_add_feedback(query: str, rating: int, comment: str = ""):
    db = get_db()
    await db.execute("INSERT INTO moat_feedback (query, rating, comment) VALUES (%s, %s, %s)",
                     (query, rating, comment))
    return {"status": "recorded", "rating": rating}

@moat_router.get("/feedback")
async def moat_list_feedback():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_feedback ORDER BY created_at DESC LIMIT 50")
    return {"feedback": rows}

# --- Moat Audit Log (2) ---
@moat_router.post("/audit")
async def moat_add_audit(action: str, actor: str = "system", details: str = "{}"):
    db = get_db()
    await db.execute("INSERT INTO moat_audit_log (action, actor, details) VALUES (%s, %s, %s)",
                     (action, actor, json.loads(details) if isinstance(details, str) else details))
    return {"status": "logged"}

@moat_router.get("/audit")
async def moat_list_audit():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_audit_log ORDER BY created_at DESC LIMIT 50")
    return {"audit_log": rows}

# --- Moat Cache (2) ---
@moat_router.get("/cache/stats")
async def moat_cache_stats():
    db = get_db()
    rows = await db.fetchall("SELECT * FROM moat_cache_meta ORDER BY hit_count DESC LIMIT 20")
    return {"cache_entries": rows}

@moat_router.delete("/cache/clear")
async def moat_clear_cache():
    redis = get_db().redis
    if redis:
        keys = []
        async for key in redis.scan_iter(f"{settings.CACHE_PREFIX}*"):
            keys.append(key)
            if len(keys) >= 1000:
                await redis.delete(*keys)
                keys = []
        if keys:
            await redis.delete(*keys)
        return {"status": "cleared", "prefix": settings.CACHE_PREFIX}
    return {"status": "no_redis"}

# --- Moat Config (2) ---
@moat_router.get("/config")
async def moat_config():
    return {"verdict_engine": settings.USE_VERDICT_ENGINE,
            "verdict_mode": settings.VERDICT_ENGINE_MODE,
            "web_search": settings.ENABLE_WEB_SEARCH,
            "targeted_search": settings.ENABLE_TARGETED_SEARCH,
            "search_domains": settings.TARGETED_SEARCH_DOMAINS,
            "llm_providers": settings.available_llm_providers,
            "cache_ttl": settings.CACHE_TTL_SECONDS,
            "rate_limit": f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW_SECONDS}s"}

@moat_router.post("/config/update")
async def moat_update_config(request: Request):
    await require_admin(request)
    body = await request.json()
    return {"status": "received", "requested_changes": body}
