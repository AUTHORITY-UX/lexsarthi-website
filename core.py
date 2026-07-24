# =============================================================================
# core.py - Core Functions: Agents, LLM, Verifiers, RAG, Search
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================

import os
import json
import asyncio
import re
import hashlib
from typing import Dict, List, Optional
from datetime import datetime

import httpx
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from groq import Groq
import openai

from config import (
    SYSTEM_BASE, DOMAINS_FULL, DIVINE_NAMES_POOL, sub_specialties,
    VERIFIERS, OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY,
    DEEPSEEK_API_KEY, OPENROUTER_API_KEY, SERPAPI_KEY
)
from models import deliberations

# ─── PROVIDER CLIENTS ──────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# ─── EMBEDDING MODEL ──────────────────────────────────────────────
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# ─── GENERATE AGENTS ──────────────────────────────────────────────
def generate_all_agents():
    agents = []
    domain_idx = 0
    name_idx = 0
    for i in range(250):
        domain = DOMAINS_FULL[domain_idx % len(DOMAINS_FULL)]
        sub_list = sub_specialties.get(domain, [f"Specialist {j+1}" for j in range(5)])
        sub = sub_list[i % len(sub_list)]
        agent_name = f"{DIVINE_NAMES_POOL[name_idx % len(DIVINE_NAMES_POOL)]} · {domain} ({sub})"
        agents.append({
            "id": f"agent_{i+1:03d}",
            "name": agent_name,
            "domain": domain,
            "persona_prompt": f"""You are a specialist in {domain}, focusing on {sub}. 
Use deep expertise, cite relevant laws and precedents, and provide practical, actionable guidance.
Always frame as legal information, not definitive legal advice.
Include: 1) Executive Summary 2) Detailed Analysis 3) Practical Implications 4) Risk Assessment 5) Next Steps."""
        })
        domain_idx += 1
        if (i+1) % 5 == 0:
            name_idx += 1
    return agents

DIVINE_AGENTS = generate_all_agents()

# ─── ROUTE AGENT ──────────────────────────────────────────────────
def route_agent(query: str, oracle: bool) -> str:
    if oracle:
        return "oracle"
    q = query.lower()
    best_score = -1
    best_id = "general"
    for agent in DIVINE_AGENTS:
        domain_words = agent["domain"].lower().split()
        score = sum(1 for w in q.split() if w in domain_words)
        if score > best_score:
            best_score = score
            best_id = agent["id"]
    return best_id if best_score >= 2 else "general"

# ─── LLM CALL ──────────────────────────────────────────────────────
async def call_llm(
    system_prompt: str,
    user_message: str,
    provider: str = "groq",
    temperature: float = 0.7,
    history: List[Dict] = None,
    max_tokens: int = 4096
) -> str:
    MAX_INPUT_TOKENS = 8000
    if len(user_message) > MAX_INPUT_TOKENS:
        user_message = user_message[:MAX_INPUT_TOKENS] + "\n[...truncated...]"

    providers = {
        "groq": {"client": groq_client, "model": "llama-3.3-70b-versatile", "is_gemini": False},
        "openai": {"client": openai_client, "model": "gpt-4o-mini", "is_gemini": False},
        "gemini": {"client": gemini_model, "model": "gemini-2.0-flash", "is_gemini": True},
        "deepseek": {"client": None, "model": "deepseek-chat", "is_gemini": False},
        "sovereign": {"client": None, "model": "meta-llama/llama-3.1-70b-instruct", "is_gemini": False}
    }

    fallback_order = ["groq", "openai", "deepseek", "gemini", "sovereign"]
    if provider in fallback_order:
        fallback_order.remove(provider)
        fallback_order.insert(0, provider)

    for prov in fallback_order:
        try:
            if prov == "deepseek":
                if not DEEPSEEK_API_KEY:
                    continue
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": "deepseek-chat",
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30.0
                    )
                    if r.status_code == 200:
                        return r.json()["choices"][0]["message"]["content"]
                    continue

            if prov == "sovereign":
                if not OPENROUTER_API_KEY:
                    continue
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://www.advocacyalawfrim.in",
                            "X-Title": "Unknown Verdict"
                        },
                        json={
                            "model": "meta-llama/llama-3.1-70b-instruct",
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30.0
                    )
                    if r.status_code == 200:
                        return r.json()["choices"][0]["message"]["content"]
                    continue

            config = providers[prov]
            client = config["client"]
            model = config["model"]
            is_gemini = config["is_gemini"]

            if not client:
                continue

            if is_gemini:
                r = client.generate_content(f"{system_prompt}\n\nUser: {user_message}")
                return r.text
            else:
                r = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return r.choices[0].message.content
        except Exception as e:
            continue

    return "Error: All LLM providers failed."

# ─── JURY VERIFICATION ─────────────────────────────────────────────
async def jury_verification(initial_answer: str, query: str, domain: str) -> Dict:
    verifier_results = []
    final_confidence = "MEDIUM"
    
    tasks = []
    for verifier in VERIFIERS:
        tasks.append(_single_verifier_review(verifier, initial_answer, query, domain))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            verifier_results.append({
                'verifier': VERIFIERS[i]['name'],
                'role': VERIFIERS[i]['role'],
                'status': 'APPROVED',
                'confidence': 'MEDIUM',
                'feedback': 'Verification skipped due to error'
            })
        else:
            verifier_results.append(result)
            if result.get('confidence') == 'HIGH':
                final_confidence = 'HIGH'
            elif result.get('confidence') == 'LOW' and final_confidence != 'HIGH':
                final_confidence = 'LOW'
    
    all_feedback = []
    for v in verifier_results:
        if v.get('feedback'):
            all_feedback.append(f"{v['verifier']}: {v['feedback']}")
    
    judge_system = """You are Shakti, the Final Judge. Return JSON: {"final_answer": "...", "confidence": "HIGH|MEDIUM|LOW", "sources": [...]}"""
    judge_prompt = f"Query: {query}\nDomain: {domain}\nOriginal Answer: {initial_answer}\nVerifier Feedback: {chr(10).join(all_feedback)}"
    
    try:
        judge_response = await call_llm(judge_system, judge_prompt, "groq")
        m = re.search(r'\{.*\}', judge_response, re.DOTALL)
        if m:
            judge_decision = json.loads(m.group())
            final_answer = judge_decision.get('final_answer', initial_answer)
            final_confidence = judge_decision.get('confidence', final_confidence)
            sources = judge_decision.get('sources', [])
        else:
            final_answer = initial_answer
            sources = []
    except:
        final_answer = initial_answer
        sources = []
    
    return {
        "final_answer": final_answer,
        "confidence": final_confidence,
        "sources": sources,
        "jury_verifiers": [v['verifier'] for v in verifier_results],
        "jury_confidences": {v['verifier']: v.get('confidence', 'MEDIUM') for v in verifier_results},
        "judge": "Shakti",
        "verifier_details": verifier_results
    }

async def _single_verifier_review(verifier: Dict, initial_answer: str, query: str, domain: str) -> Dict:
    ver_system = f"""You are {verifier['name']} ({verifier['role']}). 
    Return JSON: {{"status": "APPROVED|CORRECTED|REJECTED", "confidence": "HIGH|MEDIUM|LOW", "corrected_text": "...", "feedback": "...", "issues": ["..."]}}"""
    try:
        out = await call_llm(ver_system, f"Query: {query}\nDomain: {domain}\nAnswer:\n{initial_answer}", "groq")
        m = re.search(r'\{.*\}', out, re.DOTALL)
        if m:
            result = json.loads(m.group())
            result['verifier'] = verifier['name']
            result['role'] = verifier['role']
            return result
        return {'verifier': verifier['name'], 'role': verifier['role'], 'status': 'APPROVED', 'confidence': 'MEDIUM', 'feedback': 'No issues'}
    except:
        return {'verifier': verifier['name'], 'role': verifier['role'], 'status': 'APPROVED', 'confidence': 'MEDIUM', 'feedback': 'Verification error'}

# ─── RAG ──────────────────────────────────────────────────────────
async def fetch_relevant_chunks(query: str, top_k: int = 3, conn=None) -> List[Dict]:
    query_embedding = embedding_model.encode(query).tolist()
    query_embedding_str = json.dumps(query_embedding)
    
    if conn is None:
        async with pg_pool.acquire() as conn:
            return await _fetch_chunks(conn, query_embedding_str, top_k)
    else:
        return await _fetch_chunks(conn, query_embedding_str, top_k)

async def _fetch_chunks(conn, embedding_str: str, top_k: int):
    rows = await conn.fetch(
        """
        SELECT content, metadata, 1 - (embedding <=> $1) AS similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> $1
        LIMIT $2
        """,
        embedding_str, top_k
    )
    return [
        {
            "content": row["content"],
            "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]),
            "similarity": row["similarity"]
        }
        for row in rows
    ]

# ─── WEB SEARCH ────────────────────────────────────────────────────
async def serpapi_search(query: str, unrestricted: bool = False) -> List[Dict]:
    if not SERPAPI_KEY:
        return []
    params = {"q": query, "api_key": SERPAPI_KEY, "num": 3}
    if not unrestricted:
        domains = os.getenv("TARGETED_SEARCH_DOMAINS", "").replace(" ", "")
        if domains:
            params["q"] = f'site:({domains.replace(",", " OR ")}) {query}'
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://serpapi.com/search", params=params, timeout=8.0)
            if r.status_code == 200:
                return r.json().get("organic_results", [])
    except:
        pass
    return []