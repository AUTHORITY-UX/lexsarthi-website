# app.py – LexSarthi v3.0 (Modular Agent Registry)

import os
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Awaitable
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import PyPDF2
import pdfplumber
from openai import AsyncOpenAI
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential

# ---------- App & CORS ----------
app = FastAPI(title="LexSarthi API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://advocacyalawfrim.in", "https://www.advocacyalawfrim.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Configuration ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")
client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
MODEL = "meta-llama/llama-3.1-8b-instruct"
TOKEN_ENCODER = tiktoken.encoding_for_model("gpt-4")

# ---------- Simple Cache (TTL 5 minutes) ----------
cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # seconds

def get_cache_key(text: str, agent: str) -> str:
    return f"{agent}:{hashlib.md5(text.encode()).hexdigest()}"

def get_cached_response(key: str) -> Optional[dict]:
    if key in cache and (datetime.utcnow() - cache[key]["timestamp"]).seconds < CACHE_TTL:
        return cache[key]["data"]
    return None

def set_cached_response(key: str, data: dict):
    cache[key] = {"data": data, "timestamp": datetime.utcnow()}

# ---------- Utility: Extract text from file ----------
async def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except:
        pass
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except:
        pass
    return ""

# ---------- LLM Caller ----------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def call_llm(system: str, user: str, json_mode: bool = True) -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content

# ---------- Base Agent Type ----------
AgentHandler = Callable[[str], Awaitable[dict]]

# ---------- Agent Registry ----------
AGENT_REGISTRY: Dict[str, AgentHandler] = {}

def register_agent(name: str):
    """Decorator to register an agent handler."""
    def decorator(func: AgentHandler):
        AGENT_REGISTRY[name] = func
        return func
    return decorator

# ============================================================
#           1. Define All Agents (Using the Registry)
# ============================================================

# ---- Contract Risk ----
@register_agent("contract_risk")
async def analyze_contract_risk(text: str) -> dict:
    system = """You are a senior corporate lawyer... [same as before]"""
    user = f"Contract:\n{text[:15000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)  # simplified; you'd have extract_json_from_text

# ---- DPDP Check ----
@register_agent("dpdp_check")
async def check_dpdp(text: str) -> dict:
    system = """You are a DPDP Act specialist..."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- Legal Notice ----
@register_agent("legal_notice")
async def draft_legal_notice(text: str) -> dict:
    system = """You are a litigation lawyer..."""
    user = f"Facts:\n{text[:12000]}"
    raw = await call_llm(system, user, json_mode=True)
    return json.loads(raw)

# ---- Due Diligence ----
@register_agent("due_diligence")
async def perform_due_diligence(text: str) -> dict:
    system = """You are a due diligence expert..."""
    user = f"Documents summary:\n{text[:15000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- NDA Triage ----
@register_agent("nda_triage")
async def triage_nda(text: str) -> dict:
    system = """You are an NDA expert..."""
    user = f"NDA:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- Weekly Digest ----
@register_agent("weekly_digest")
async def generate_digest(text: str) -> dict:
    # text is actually the topic
    system = f"""You are a legal assistant. Summarise key legal developments related to '{text}'."""
    raw = await call_llm(system, user="Generate digest", json_mode=True)
    return json.loads(raw)

# ---- Consent Form ----
@register_agent("consent_form")
async def generate_consent(text: str) -> dict:
    # text = "Purpose: ... Data: ..."
    system = f"""You are a privacy lawyer... {text}"""
    raw = await call_llm(system, user="Generate consent form", json_mode=True)
    return json.loads(raw)

# ---- Domain Review ----
@register_agent("domain_review")
async def analyze_domain_agreement(text: str) -> dict:
    system = """You are a domain agreement expert..."""
    user = f"Domain Agreement:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- Oral Arguments ----
@register_agent("oral_arguments")
async def prepare_oral_arguments(text: str) -> dict:
    system = """You are a senior advocate..."""
    user = f"Case details:\n{text[:15000]}"
    raw = await call_llm(system, user, json_mode=True)
    return json.loads(raw)

# ---- NEW: M&A Due Diligence (Example) ----
@register_agent("ma_due_diligence")
async def ma_due_diligence(text: str) -> dict:
    system = """You are a M&A due diligence expert. Analyse the provided documents for deal risks."""
    user = f"Documents:\n{text[:15000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- NEW: Employment Law Compliance ----
@register_agent("employment_law")
async def employment_law(text: str) -> dict:
    system = """You are an employment law expert. Analyse the provided employment contract or policy."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- NEW: IP Filing Assistant ----
@register_agent("ip_filing")
async def ip_filing(text: str) -> dict:
    system = """You are an IP lawyer. Assist with patent/trademark filing strategy based on the provided invention/brand."""
    user = f"Details:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ---- NEW: Tax Compliance Check ----
@register_agent("tax_compliance")
async def tax_compliance(text: str) -> dict:
    system = """You are a tax lawyer. Check the provided document for compliance with Indian tax laws."""
    user = f"Document:\n{text[:12000]}"
    raw = await call_llm(system, user)
    return json.loads(raw)

# ============================================================
#           2. Core Endpoint Using the Registry
# ============================================================

@app.post("/run-agent")
async def run_agent(
    agent_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    # Check if agent exists
    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(400, f"Unknown agent: {agent_name}")

    # Extract content
    content = ""
    if file:
        file_bytes = await file.read()
        content = await extract_text_from_file(file_bytes, file.filename)
    elif text:
        content = text
    else:
        raise HTTPException(400, "No input provided")
    if len(content.strip()) < 50:
        raise HTTPException(400, "Input too short")

    # Cache check
    cache_key = get_cache_key(content, agent_name)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    # Run agent
    handler = AGENT_REGISTRY[agent_name]
    result = await handler(content)

    # Cache result
    set_cached_response(cache_key, result)

    return result

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Optional: list all registered agents
@app.get("/agents")
async def list_agents():
    return {"agents": list(AGENT_REGISTRY.keys())}