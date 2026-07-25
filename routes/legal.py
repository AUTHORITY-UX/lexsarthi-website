# routes/legal.py - Legal Intelligence Routes
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List, Dict
from datetime import datetime

from core import DIVINE_AGENTS, call_llm, route_agent, jury_verification
from models import users

router = APIRouter(prefix="/api/legal", tags=["Legal"])

@router.get("/agents")
async def list_legal_agents():
    """List all 250 legal agents"""
    legal_agents = [a for a in DIVINE_AGENTS if a["type"] == "legal"]
    return {
        "status": "ok",
        "count": len(legal_agents),
        "agents": legal_agents,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/ask")
async def legal_query(
    query: str = Form(...),
    domain: Optional[str] = Form(None),
    cu: dict = Depends(get_current_user)
):
    """Ask a legal question"""
    if cu["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(403, "Premium+ required")
    
    agent_id = route_agent(query, False)
    agent = next((a for a in DIVINE_AGENTS if a["id"] == agent_id), None)
    agent_name = agent["name"] if agent else "General Council"
    domain = agent["domain"] if agent else "General"
    persona = agent["persona_prompt"] if agent else "You are a generalist."
    
    system_prompt = f"""You are a legal specialist. Domain: {domain}
Agent: {agent_name}
Persona: {persona}

Provide expert legal advice. Cite relevant sections and precedents."""
    
    initial_answer = await call_llm(system_prompt, query, "groq")
    jury_result = await jury_verification(initial_answer, query, domain)
    
    return {
        "status": "ok",
        "answer": jury_result["final_answer"],
        "confidence": jury_result["confidence"],
        "sources": jury_result["sources"],
        "agent": agent_name,
        "domain": domain,
        "verifiers": jury_result["jury_verifiers"],
        "timestamp": datetime.now().isoformat()
    }

@router.post("/contract/draft")
async def draft_contract(
    name: str = Form(...),
    party_a: str = Form(...),
    party_b: str = Form(...),
    purpose: str = Form(...),
    term: int = Form(12),
    cu: dict = Depends(get_current_user)
):
    """Draft a legal contract"""
    if cu["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(403, "Premium+ required")
    
    prompt = f"""
    Draft a professional contract between {party_a} and {party_b} for {purpose}.
    Name: {name}
    Term: {term} months
    
    Include:
    1. Definitions
    2. Obligations
    3. Payment terms
    4. Term and termination
    5. Confidentiality
    6. Governing law (India)
    7. Dispute resolution
    8. Signatures
    """
    
    result = await call_llm("You are a contract drafting specialist.", prompt, "groq")
    return {
        "status": "ok",
        "contract": result,
        "name": name,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/research")
async def legal_research(
    query: str = Form(...),
    jurisdiction: str = Form("IN"),
    cu: dict = Depends(get_current_user)
):
    """Legal research with case law and precedents"""
    if cu["tier"] not in ("premium", "enterprise", "lifetime"):
        raise HTTPException(403, "Premium+ required")
    
    prompt = f"""
    Research this legal topic: {query}
    Jurisdiction: {jurisdiction}
    
    Provide:
    1. Relevant sections of law
    2. Key case law and precedents
    3. Legal analysis
    4. Practical implications
    5. Risks and recommendations
    """
    
    result = await call_llm("You are a legal researcher.", prompt, "groq")
    return {
        "status": "ok",
        "research": result,
        "jurisdiction": jurisdiction,
        "timestamp": datetime.now().isoformat()
    }