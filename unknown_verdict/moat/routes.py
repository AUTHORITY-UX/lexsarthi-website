"""All Moat v41.0 FastAPI routes under /api/moat."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from loguru import logger as log

from .db import db
from .evolution import evolution
from .reasoning import irac_engine
from .dynamic_rag import dynamic_rag
from .judge_evolution import judge_evolution
from .predictive import predictive
from .emotion import emotion
from .strategy import strategy_gen
from .vault import vault
from .pricing import pricing
from .publishing import publishing
from .marketplace import marketplace

moat_router = APIRouter(tags=["Moat v41.0"])

# --- Request models ---
class TextReq(BaseModel):
    text: str = ""
    query: str = ""
    case_summary: str = ""
    jurisdiction: str = "IN"
    agent_id: str = ""

class InteractionReq(BaseModel):
    agent_id: str
    query: str
    response: str = ""
    outcome: str = "unknown"
    confidence_delta: float = 0.0

class IRACReq(BaseModel):
    case_summary: str
    jurisdiction: str = "IN"
    agent_id: str = ""
    precedents: List[str] = []

class DocReq(BaseModel):
    content: str
    source_url: str = ""
    title: str = ""
    citation: str = ""
    jurisdiction: str = "IN"
    court: str = ""

class VerdictReq(BaseModel):
    case_summary: str
    agent_response: str = ""
    agent_name: str = ""
    jurisdiction: str = "IN"

class ResolveReq(BaseModel):
    verdict_id: str
    actual_outcome: str
    feedback: float = 0.0

class PredictionReq(BaseModel):
    case_summary: str
    case_type: str = "civil"
    jurisdiction: str = "IN"

class EmotionReq(BaseModel):
    client_text: str
    legal_query: str = ""

class StrategyReq(BaseModel):
    case_summary: str
    jurisdiction: str = "IN"

class ArticleReq(BaseModel):
    topic: str
    keywords: List[str] = []

class NewsletterReq(BaseModel):
    topics: List[str]

class ListingReq(BaseModel):
    listing_type: str
    title: str
    description: str
    price_inr: int = 0
    creator_id: str = ""
    metadata: Dict = {}

class MatchReq(BaseModel):
    case_type: str
    budget_inr: int = 0

class CrossJurReq(BaseModel):
    case_summary: str
    jurisdictions: List[str] = ["IN", "US", "UK"]

class GapReq(BaseModel):
    query: str
    agent_id: str
    confidence: float = 0.5

class SearchReq(BaseModel):
    query: str
    top_k: int = 8

# --- Lifecycle ---
@moat_router.on_event("startup")
async def _startup():
    await db.init()

@moat_router.on_event("shutdown")
async def _shutdown():
    await db.close()

# --- System ---
@moat_router.get("/status")
async def moat_status():
    s = await db.stats()
    return {"version":"41.0.0","db":s,"modules":["evolution","irac","rag","judge",
            "predictive","emotion","strategy","vault","pricing","publishing","marketplace"]}

# --- Feature 1: Self-Evolving Agents ---
@moat_router.post("/evolution/record")
async def record_learning(req: InteractionReq):
    return await evolution.record_interaction(req.agent_id, req.query, req.response, req.outcome, req.confidence_delta)

@moat_router.post("/evolution/recall")
async def recall_learnings(req: SearchReq):
    return {"results": await evolution.recall_learnings(req.query, req.top_k)}

@moat_router.post("/evolution/mesh")
async def mesh_knowledge(req: SearchReq):
    return {"results": await evolution.get_mesh_knowledge(req.query, req.top_k)}

@moat_router.post("/evolution/training-data/{agent_id}")
async def training_data(agent_id: str, limit: int = 20):
    return {"training_pairs": await evolution.generate_training_data(agent_id, limit)}

@moat_router.post("/evolution/detect-gap")
async def detect_gap(req: GapReq):
    result = await evolution.detect_knowledge_gap(req.query, req.agent_id, req.confidence)
    if result and result.get("gap_detected"):
        created = await evolution.auto_create_agent(result)
        return {"gap_detected": True, "proposal": result, "new_agent": created}
    return {"gap_detected": False}

# --- Feature 2: IRAC Reasoning ---
@moat_router.post("/irac/reason")
async def irac_reason(req: IRACReq):
    return await irac_engine.reason(req.case_summary, req.jurisdiction, req.agent_id, req.precedents)

@moat_router.post("/irac/cross-jurisdiction")
async def irac_cross_jur(req: CrossJurReq):
    return await irac_engine.cross_jurisdiction(req.case_summary, req.jurisdictions)

@moat_router.post("/irac/search")
async def irac_search(req: SearchReq):
    return {"patterns": await irac_engine.search_patterns(req.query, req.top_k)}

# --- Feature 3: Dynamic RAG ---
@moat_router.post("/rag/add")
async def rag_add(req: DocReq):
    return await dynamic_rag.add_document(req.content, req.source_url, req.title, req.citation, req.jurisdiction, req.court)

@moat_router.post("/rag/search")
async def rag_search(req: SearchReq):
    return {"results": await dynamic_rag.search(req.query, req.top_k)}

@moat_router.get("/rag/crawl")
async def rag_crawl():
    return await dynamic_rag.auto_crawl()

@moat_router.get("/rag/versions/{citation}")
async def rag_versions(citation: str):
    return {"versions": await dynamic_rag.get_version_history(citation)}

# --- Feature 4: Judge Evolution ---
@moat_router.post("/judge/verdict")
async def judge_verdict(req: VerdictReq):
    return await judge_evolution.deliver_verdict(req.case_summary, req.agent_response, req.agent_name)

@moat_router.post("/judge/resolve")
async def judge_resolve(req: ResolveReq):
    return await judge_evolution.resolve_with_feedback(req.verdict_id, req.actual_outcome, req.feedback)

@moat_router.get("/judge/stats")
async def judge_stats():
    return await judge_evolution.get_evolution_stats()

# --- Feature 5: Predictive Analytics ---
@moat_router.post("/predict/outcome")
async def predict_outcome(req: PredictionReq):
    return await predictive.predict_outcome(req.case_summary, req.case_type, req.jurisdiction)

@moat_router.post("/predict/settlement")
async def predict_settlement(req: TextReq):
    return await predictive.predict_settlement(req.case_summary or req.text)

@moat_router.post("/predict/timeline")
async def predict_timeline(req: PredictionReq):
    return await predictive.predict_timeline(req.case_summary, req.case_type)

@moat_router.post("/predict/cost")
async def predict_cost(req: PredictionReq):
    return await predictive.predict_cost(req.case_summary, req.case_type)

# --- Feature 6: Emotion-Aware Analysis ---
@moat_router.post("/emotion/analyze")
async def emotion_analyze(req: EmotionReq):
    return await emotion.analyze_and_respond(req.client_text, req.legal_query)

# --- Feature 10: Strategy Generator ---
@moat_router.post("/strategy/generate")
async def strategy_generate(req: StrategyReq):
    return await strategy_gen.generate_strategy(req.case_summary, req.jurisdiction)

# --- Feature 11: Data Vault ---
@moat_router.get("/vault/audit/{entity_id}")
async def vault_audit(entity_id: str):
    return {"trail": await vault.get_forensic_trail(entity_id)}

@moat_router.get("/vault/audit")
async def vault_audit_all(limit: int = 50):
    return {"trail": await vault.get_forensic_trail("", limit)}

@moat_router.get("/vault/verify/{entity_id}")
async def vault_verify(entity_id: str):
    return await vault.verify_integrity(entity_id)

@moat_router.get("/vault/inventory")
async def vault_inventory():
    return await vault.get_ip_inventory()

# --- Feature 14: Pricing ---
@moat_router.post("/pricing/case")
async def price_case(req: PredictionReq):
    return await pricing.price_case(req.case_summary, req.case_type)

@moat_router.post("/pricing/value-report")
async def value_report(req: TextReq):
    return await pricing.value_report(req.case_summary or req.text)

# --- Feature 16: Publishing ---
@moat_router.post("/publishing/article")
async def gen_article(req: ArticleReq):
    return await publishing.generate_article(req.topic, req.keywords)

@moat_router.post("/publishing/newsletter")
async def gen_newsletter(req: NewsletterReq):
    return await publishing.generate_newsletter(req.topics)

@moat_router.post("/publishing/social")
async def gen_social(topic: str):
    return await publishing.generate_social_post(topic)

@moat_router.get("/publishing/drafts")
async def list_drafts(status: str = "draft"):
    return {"drafts": await publishing.list_drafts(status)}

# --- Features 17 & 18: Marketplace ---
@moat_router.post("/marketplace/create")
async def create_listing(req: ListingReq):
    return await marketplace.create_listing(req.listing_type, req.title, req.description, req.price_inr, req.creator_id, req.metadata)

@moat_router.get("/marketplace/agents")
async def list_agents():
    return {"listings": await marketplace.list_agents()}

@moat_router.get("/marketplace/templates")
async def list_templates():
    return {"listings": await marketplace.list_templates()}

@moat_router.post("/marketplace/search")
async def market_search(query: str):
    return {"results": await marketplace.search(query)}

@moat_router.post("/marketplace/match")
async def market_match(req: MatchReq):
    return await marketplace.client_lawyer_match(req.case_type, req.budget_inr)
