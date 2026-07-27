# ============================================
# CORE.PY – REAL AI ENGINE
# ============================================

import os
import logging
from typing import Dict, Any
import openai
import groq
import google.generativeai as genai
import PyPDF2
from io import BytesIO

logger = logging.getLogger("unknown_verdict")

# ============================================
# LOAD YOUR REAL KEYS
# ============================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Initialize real clients
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')

logger.info("✅ REAL AI Clients initialized")

# ============================================
# REAL LEGAL KNOWLEDGE BASE (From Your PDFs!)
# ============================================

class LegalKnowledgeBase:
    def __init__(self):
        self.documents = []
        self._load_pdfs()
    
    def _load_pdfs(self):
        """Load your real PDF legal documents"""
        pdf_files = [
            "AIACT.pdf",
            "DPDPA.pdf", 
            "Indian contract act.pdf",
            "companies act.pdf",
            "the_constitution_of_india.pdf",
            "EVIDENCE_ACT.pdf",
            "DATA_ACT.pdf"
        ]
        
        for pdf_file in pdf_files:
            try:
                if os.path.exists(pdf_file):
                    with open(pdf_file, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text()
                        self.documents.append({
                            "name": pdf_file,
                            "content": text[:5000]  # First 5000 chars
                        })
                        logger.info(f"✅ Loaded {pdf_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load {pdf_file}: {e}")
        
        logger.info(f"📚 Loaded {len(self.documents)} real legal documents")

# ============================================
# REAL AI JUDGE
# ============================================

class RealAIJudge:
    def __init__(self):
        self.knowledge = LegalKnowledgeBase()
    
    async def process(self, query: str) -> Dict:
        """Process with REAL AI"""
        try:
            # Try OpenAI first
            if openai_client:
                response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an AI Judge. Answer legal questions based on Indian law."},
                        {"role": "user", "content": query}
                    ]
                )
                return {
                    "response": response.choices[0].message.content,
                    "agent": "AI Judge (OpenAI)",
                    "confidence": 0.92
                }
            
            # Fallback to Groq
            elif groq_client:
                response = groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[
                        {"role": "system", "content": "You are an AI Judge. Answer legal questions based on Indian law."},
                        {"role": "user", "content": query}
                    ]
                )
                return {
                    "response": response.choices[0].message.content,
                    "agent": "AI Judge (Groq)",
                    "confidence": 0.88
                }
            
            # Fallback to Gemini
            elif GEMINI_API_KEY:
                response = gemini_model.generate_content(query)
                return {
                    "response": response.text,
                    "agent": "AI Judge (Gemini)",
                    "confidence": 0.85
                }
            
            else:
                return {
                    "response": "No AI API keys configured. Please add OPENAI_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY.",
                    "agent": "System",
                    "confidence": 0.0
                }
                
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "agent": "System",
                "confidence": 0.0
            }

# ============================================
# REAL MARKET DATA
# ============================================

import yfinance as yf
import asyncio

async def get_real_markets():
    try:
        symbols = ["^NSEI", "^BSESN", "BTC-USD", "ETH-USD"]
        data = {}
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            data[symbol] = {
                "price": info.get("regularMarketPrice", 0),
                "change": info.get("regularMarketChangePercent", 0)
            }
        return data
    except Exception as e:
        logger.error(f"Market data error: {e}")
        return {}

# ============================================
# REAL NEWS
# ============================================

import feedparser

def get_real_news():
    sources = [
        "https://www.law.com/legaltechnews/feed",
        "https://www.indialegallive.com/feed",
        "https://techcrunch.com/feed"
    ]
    articles = []
    for url in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "source": url.split("/")[2]
                })
        except:
            pass
    return articles

# ============================================
# REAL COMPLIANCE SCANNER
# ============================================

import requests
from bs4 import BeautifulSoup

async def scan_website(url):
    try:
        response = requests.get(url, timeout=10)
        text = response.text.lower()
        frameworks = {
            "GDPR": "gdpr" in text or "general data protection" in text,
            "DPDPA": "dpdpa" in text or "digital personal data" in text,
            "CCPA": "ccpa" in text or "california consumer privacy" in text
        }
        return frameworks
    except:
        return {"error": "Could not scan website"}

# ============================================
# EXPORTS
# ============================================

_judge_instance = None

def get_judge():
    global _judge_instance
    if _judge_instance is None:
        _judge_instance = RealAIJudge()
    return _judge_instance

__all__ = ['RealAIJudge', 'get_judge', 'get_real_markets', 'get_real_news', 'scan_website']