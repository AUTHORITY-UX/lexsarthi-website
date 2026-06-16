# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import os, json, logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llama_index.llms.groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

llm = Groq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0.1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lexsarthi")

app = FastAPI(title="LexSarthi AI Law Firm OS", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["https://advocacyalawfrim.in", "http://localhost:3000"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ContractAnalysisRequest(BaseModel):
    text: Optional[str] = None
    file_url: Optional[str] = None
    lawyer_review: bool = False

class AgentRequest(BaseModel):
    input_text: str
    metadata: Optional[Dict[str, Any]] = {}

def generate(prompt: str) -> str:
    return llm.complete(prompt).text.strip()

def safe_json_parse(raw: str) -> dict:
    try: return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")+1
        if s!=-1 and e>s: return json.loads(raw[s:e])
        raise

def extract_text_from_pdf(file_url: str) -> str:
    import requests, io
    from pypdf import PdfReader
    resp = requests.get(file_url, timeout=15)
    resp.raise_for_status()
    reader = PdfReader(io.BytesIO(resp.content))
    return "".join(page.extract_text() or "" for page in reader.pages)

@app.get("/")
async def root():
    return {"status": "LexSarthi API running", "docs": "/docs"}

@app.get("/analyze")
async def analyze_get():
    return JSONResponse({"message": "Please use POST /analyze with JSON body (text or file_url).",
                         "example": {"text": "...", "lawyer_review": False},
                         "live_demo": "https://advocacyalawfrim.in"})

@app.post("/analyze")
async def analyze_contract(payload: ContractAnalysisRequest):
    text = payload.text
    if not text and payload.file_url: text = extract_text_from_pdf(payload.file_url)
    if not text: raise HTTPException(400, "No text provided")
    prompt = f"""You are an Indian contract law expert. Analyze the contract clause-by-clause. Return JSON:
{{"summary": "...", "clauses": [{{"clause_name": "...", "risk": "High/Medium/Low", "legal_basis": "...", "suggestion": "..."}}],
  "missing_clauses": ["..."], "lawyer_review": null}}
Lawyer review requested: {payload.lawyer_review}
Contract:
{text[:6000]}
JSON:"""
    raw = generate(prompt)
    try: result = safe_json_parse(raw)
    except: result = {"summary": "Parsing error", "clauses": [], "missing_clauses": [], "lawyer_review": None}
    if payload.lawyer_review:
        result["lawyer_review"] = "Simulated review: This contract appears balanced. I recommend clarifying the indemnity clause. – Advocate [Founder]"
    return result

@app.post("/dpdp-check")
async def dpdp_check(payload: AgentRequest):
    prompt = f"""Review this document for DPDP Act compliance. Return JSON: is_compliant (bool), issues (list), recommendations (list).
Document:
{payload.input_text[:5000]}
JSON:"""
    return safe_json_parse(generate(prompt))

@app.post("/legal-notice")
async def legal_notice(payload: AgentRequest):
    prompt = f"""Draft a formal legal notice (India). Return JSON: notice_title, body, statutory_references (list).
Facts:
{payload.input_text[:4000]}
JSON:"""
    return safe_json_parse(generate(prompt))

@app.post("/due-diligence")
async def due_diligence(payload: AgentRequest):
    prompt = f"""Perform legal due diligence. Return JSON: summary, risks (list), compliance_gaps (list), recommendations (list).
Info:
{payload.input_text[:5000]}
JSON:"""
    return safe_json_parse(generate(prompt))

@app.post("/nda-triage")
async def nda_triage(payload: AgentRequest):
    prompt = f"""Triage this NDA. Return JSON: overall_risk (High/Medium/Low), dangerous_clauses (list with explanations), negotiation_tips (list).
NDA Text:
{payload.input_text[:5000]}
JSON:"""
    return safe_json_parse(generate(prompt))

@app.post("/weekly-digest")
async def weekly_digest(payload: AgentRequest):
    prompt = f"""Summarize Indian legal updates. Return JSON: title, highlights (list), impact (string).
Context:
{payload.input_text[:3000]}
JSON:"""
    return safe_json_parse(generate(prompt))

@app.post("/consent-form")
async def consent_form(payload: AgentRequest):
    prompt = f"""Create a DPDP-compliant consent form. Return JSON: form_title, consent_text, mandatory_clauses (list).
Details:
{payload.input_text[:3000]}
JSON:"""
    return safe_json_parse(generate(prompt))

@app.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):
    data = await request.json()
    logger.info(f"Razorpay event: {data.get('event')}")
    return {"status": "ok"}

def load_document():
    legal_docs = Path("legal_docs")
    for file in legal_docs.glob("*"):
        if file.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(file)
            return "".join(page.extract_text() or "" for page in reader.pages)
        elif file.suffix.lower() == ".txt":
            return file.read_text(encoding="utf-8")
    return None

DOCUMENT = load_document()
if DOCUMENT:
    print(f"Legal doc loaded for chat: {len(DOCUMENT)} chars")
    import gradio as gr
    def gradio_chat_fn(message, history):
        ctx = DOCUMENT[:6000]
        prompt = f"""You are a legal assistant. Use the document below to answer.
Document:
{ctx}
Question: {message}
Answer:"""
        return generate(prompt)
    chat_ui = gr.ChatInterface(fn=gradio_chat_fn, title="LexSarthi Legal Chat", description="Ask about the uploaded document.")
    app = gr.mount_gradio_app(app, chat_ui, path="/chat")