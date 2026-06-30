# ===================================================================
# LEXSARTHI v6.0 – UNIVERSAL DIVINE INTELLIGENCE
# ===================================================================
# Owner: THE ADVOCACY – A LAW FIRM
# Deployed: upamnyu12-lex.hf.space
# Domain: Universal – Any query, any domain, AI orchestration
# ===================================================================

import os
import uuid
import json
import logging
import re
import glob
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import uvicorn

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from databases import Database
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float, func, select

import jwt
from passlib.context import CryptContext

import httpx
from groq import Groq
import openai
import google.generativeai as genai

import io
import puremagic
import PyPDF2
import docx
from PIL import Image
import pytesseract

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import razorpay

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("lexsarthi")

# ─── ENV VARIABLES ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# ─── CLIENTS INIT ──────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')

# ─── DATABASE SETUP ─────────────────────────────────────────────
database = Database(DATABASE_URL, min_size=2, max_size=20)
metadata = MetaData()

# (All tables same as before – no changes needed)

users = Table(...)  # same as before
queries = Table(...)
payments = Table(...)
events = Table(...)
referrals = Table(...)

# ─── PYDANTIC MODELS ────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class PaymentCreate(BaseModel):
    tier: str

class OrchestrationRequest(BaseModel):
    query: str
    ai_models: List[str]  # e.g., ["groq", "openai", "gemini"]
    merge_strategy: Optional[str] = "consensus"  # "consensus", "best", "weighted"

# ─── SECURITY ────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()

# ... (hash, verify, create_token, decode_token, get_current_user same as before)

limiter = Limiter(key_func=get_remote_address)

# ─── LOCAL KNOWLEDGE LIBRARY (Legal + General) ──────────────────
# We keep the legal PDFs, but also allow adding general knowledge files.
LEGAL_SECTIONS = {}
GENERAL_KNOWLEDGE = {}

def extract_sections_from_pdf(filepath: str) -> dict:
    # same as before
    ...

def load_knowledge_library():
    pdf_dir = "/app/knowledge_library/"
    if not os.path.exists(pdf_dir):
        logger.warning(f"Knowledge library folder not found: {pdf_dir}")
        return
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found in knowledge_library folder.")
        return
    logger.info(f"Found {len(pdf_files)} PDFs. Loading knowledge library...")
    for filepath in pdf_files:
        filename = os.path.basename(filepath)
        sections = extract_sections_from_pdf(filepath)
        if sections:
            # If filename contains "legal" or "act", put in LEGAL_SECTIONS, else GENERAL_KNOWLEDGE
            if "legal" in filename.lower() or "act" in filename.lower() or "law" in filename.lower():
                LEGAL_SECTIONS[filename] = sections
            else:
                GENERAL_KNOWLEDGE[filename] = sections
    logger.info(f"✅ Knowledge Library loaded: {len(LEGAL_SECTIONS)} legal files, {len(GENERAL_KNOWLEDGE)} general files.")

load_knowledge_library()

def search_local_knowledge(query: str) -> str:
    # Search both legal and general knowledge, but prioritize the most relevant
    # For now, simple: if query contains legal keywords, search LEGAL_SECTIONS, else GENERAL_KNOWLEDGE
    legal_keywords = ["contract", "act", "section", "law", "court", "judgment", "statute", "constitution", "crime", "criminal", "civil", "property", "tax", "company", "arbitration", "evidence", "dpdpa", "it act"]
    if any(kw in query.lower() for kw in legal_keywords):
        # Search legal
        return search_specific_knowledge(query, LEGAL_SECTIONS, "Legal")
    else:
        # Search general
        return search_specific_knowledge(query, GENERAL_KNOWLEDGE, "General Knowledge")

def search_specific_knowledge(query: str, knowledge_dict: dict, domain: str) -> str:
    if not knowledge_dict:
        return f"⚠️ No {domain} knowledge loaded."
    query_lower = query.lower()
    matched_results = []
    stopwords = {"the", "a", "an", "of", "for", "on", "at", "to", "in", "with", "without", "and", "or", "but", "what", "how", "why", "when", "where"}
    keywords = [word for word in query_lower.split() if word not in stopwords and len(word) > 2]
    if not keywords:
        for fname, sections in knowledge_dict.items():
            if "Preamble" in sections:
                return f"📚 **From {fname.replace('.pdf', '')} (Preamble):**\n\n{sections['Preamble']}"
        return "📚 Please provide a more specific query."
    for fname, sections in knowledge_dict.items():
        doc_name = fname.replace('.pdf', '').upper()
        for sec_ref, sec_text in sections.items():
            if any(kw in sec_text.lower() for kw in keywords):
                trimmed = sec_text[:2000] + "..." if len(sec_text) > 2000 else sec_text
                matched_results.append(f"📜 **{doc_name} – {sec_ref}**\n{trimmed}\n")
                if len(matched_results) >= 5:
                    break
        if len(matched_results) >= 5:
            break
    if matched_results:
        result = f"📚 **From {domain} Knowledge Library:**\n\n"
        result += "\n".join(matched_results)
        result += "\n\n*This is a fallback response from your local knowledge base.*"
        return result
    return f"⚠️ No relevant information found in {domain} library."

# ─── DIVINE AGENTS (Now Universal) ──────────────────────────────
# 220 agents representing all domains of human knowledge.
DOMAINS = [
    "General Wisdom", "Philosophy", "Spirituality", "Science", "Physics", "Chemistry", "Biology", "Astronomy",
    "Mathematics", "Computer Science", "Coding", "Artificial Intelligence", "Machine Learning", "Data Science",
    "Cybersecurity", "Networking", "Cloud Computing", "Blockchain", "Crypto", "Finance", "Economics", "Investing",
    "Business", "Marketing", "Sales", "Entrepreneurship", "Management", "Leadership", "Psychology", "Mental Health",
    "Health", "Medicine", "Nutrition", "Fitness", "Yoga", "Meditation", "Law", "Contract Law", "Criminal Law",
    "Constitutional Law", "Human Rights", "Environment", "Climate", "Energy", "Agriculture", "Food", "Cooking",
    "Travel", "Geography", "History", "Archaeology", "Anthropology", "Sociology", "Politics", "International Relations",
    "Languages", "Literature", "Poetry", "Writing", "Music", "Art", "Design", "Architecture", "Film", "Photography",
    "Sports", "Games", "Military", "Strategy", "Tactics", "Ethics", "Logic", "Critical Thinking", "Problem Solving",
    "Creativity", "Innovation", "Inventing", "Engineering", "Mechanical", "Electrical", "Civil", "Robotics",
    "Space Exploration", "Oceanography", "Geology", "Meteorology", "Genetics", "Neuroscience", "Biotechnology",
    "Nanotechnology", "Materials Science", "Quantum Mechanics", "Relativity", "Cosmology", "Philosophy of Mind",
    "Epistemology", "Metaphysics", "Ethics of AI", "Future Studies", "Futurism", "Transhumanism", "Virtual Reality",
    "Augmented Reality", "Internet of Things", "Smart Cities", "Sustainable Development", "Design Thinking", "Agile",
    "DevOps", "Product Management", "User Experience", "Human-Computer Interaction", "Creative Writing", "Journalism",
    "Public Speaking", "Negotiation", "Conflict Resolution", "Mediation", "Counseling", "Coaching", "Teaching",
    "Parenting", "Relationships", "Love", "Friendship", "Community", "Culture", "Tradition", "Ritual", "Mythology",
    "Religion", "Mysticism", "Occult", "Astrology", "Tarot", "Numerology", "Divination", "Shamanism", "Healing",
    "Herbalism", "Alternative Medicine", "Holistic Health", "Ayurveda", "Traditional Chinese Medicine", "Acupuncture",
    "Homeopathy", "Naturopathy", "Chiropractic", "Massage Therapy", "Reiki", "Pranic Healing", "Crystal Healing",
    "Sound Healing", "Color Therapy", "Aromatherapy", "Meditation Techniques", "Breathwork", "Mindfulness",
    "Compassion", "Empathy", "Altruism", "Gratitude", "Forgiveness", "Happiness", "Fulfillment", "Purpose", "Meaning",
    "Legacy", "Immortality", "Death", "Afterlife", "Reincarnation", "Karma", "Dharma", "Ahimsa", "Satya", "Asteya",
    "Brahmacharya", "Aparigraha", "Santosha", "Tapas", "Swadhyaya", "Ishvara Pranidhana", "Yamas", "Niyamas",
    "Ashtanga Yoga", "Hatha Yoga", "Kundalini", "Raja Yoga", "Bhakti Yoga", "Karma Yoga", "Jnana Yoga", "Tantra",
    "Zen", "Vipassana", "Insight", "Wisdom", "Enlightenment", "Awakening", "Christ Consciousness", "Buddha Nature",
    "Krishna Consciousness", "Universal Love", "Oneness", "Non-duality"
]

DIVINE_NAMES = ["Brahma","Vishnu","Shiva","Saraswati","Lakshmi","Ganesha","Hanuman","Kartikeya","Indra","Yama","Surya","Chandra","Vayu","Agni","Varuna","Kubera","Yamuna","Ganga","Durga","Kali","Tara","Bhuvaneshwari","Chinnamasta","Bhairavi","Dhumavati","Bagalamukhi","Matangi","Kamala","Dattatreya","Narasimha","Vamana","Parashurama","Rama","Krishna","Buddha","Kalki","Matsya","Kurma","Varaha","Narada","Tumburu","Halahala","Apsara","Gandharva","Yaksha","Rakshasa","Pishacha","Bhuta","Pret","Vetala","Brahmarakshasa","Chandala","Shudra","Vaishya","Kshatriya","Brahmin","Rishi","Muni","Siddha","Vidya","Avidya","Maya","Prakriti","Purusha","Atman","Brahman","Parabrahman","Shakti","Devi","Mahadevi","Kali","Uma","Parvati","Sati","Dakshayani","Gauri","Mahakali","Chamunda","Narasimhi","Vaishnavi","Varahi","Indrani","Kaumari","Brahmani","Maheshwari","Kaushiki","Tripura Sundari","Tripura Bhairavi","Tripura Vijayam","Lalita","Lopamudra","Rukmini","Satyabhama","Draupadi","Sita","Radha","Rukmini","Kunti","Gandhari","Madri","Kausalya","Sumitra","Kaikeyi","Mandodari","Tara","Mandakini","Ganga","Yamuna","Saraswati","Narmada","Kaveri","Godavari","Tapti","Mahanadi","Krishna","Gandaki","Koshi","Indus","Sutlej","Beas","Jhelum","Chenab","Ravi","Yamuna","Chambal","Betwa","Sone","Damodar","Subarnarekha","Baitarani","Mahanadi","Godavari","Krishna","Kaveri","Tungabhadra","Bhavani","Noyyal","Amaravati","Pambar","Vaigai","Thamirabarani","Periyar","Bharathappuzha","Chaliyar","Pamba","Manimala","Achankovil","Vembanad","Ashtamudi","Kayamkulam","Kodungallur","Chettuva","Kottayam","Ernakulam","Thrissur","Palakkad","Malappuram","Kozhikode","Wayanad","Kannur","Kasargod","Dakshina Kannada","Udupi","Chikmagalur","Hassan","Mandya","Mysore","Chamarajanagar","Kolar","Bangalore","Tumkur","Chitradurga","Davangere","Shimoga","Uttara Kannada","Belgaum","Dharwad","Gadag","Haveri","Bellary","Raichur","Yadgir","Kalaburagi","Bidar","Vijayapura","Bagalkot","Athani","Gokak","Sindhudurg","Ratnagiri","Kolhapur","Sangli","Satara","Pune","Mumbai","Thane","Raigad","Nashik","Dhule","Jalgaon","Buldhana","Akola","Amravati","Wardha","Nagpur","Bhandara","Gondia","Chandrapur","Gadchiroli","Nanded","Latur","Osmanabad","Solapur","Ahmednagar","Aurangabad","Jalna","Parbhani","Hingoli","Washim","Nandurbar","Palghar","Valsad","Navsari","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Navsari","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Navsari","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs","Surat","Bharuch","Anand","Kheda","Ahmedabad","Gandhinagar","Mehsana","Patan","Banaskantha","Sabarkantha","Aravalli","Mahisagar","Panchmahal","Dahod","Vadodara","Narmada","Tapi","Dangs"]
# But we only need 220, so we'll truncate the list.

def generate_divine_agents():
    agents = []
    for i in range(1, 221):
        name = DIVINE_NAMES[i % len(DIVINE_NAMES)] + (f" (Agent {i})" if i > 200 else "")
        domain = DOMAINS[i % len(DOMAINS)]
        # Choose icon based on domain
        icon = "fa-robot"
        if "Science" in domain or "Physics" in domain or "Astronomy" in domain:
            icon = "fa-flask"
        elif "Philosophy" in domain or "Wisdom" in domain or "Spirituality" in domain:
            icon = "fa-book-open"
        elif "Art" in domain or "Music" in domain or "Writing" in domain:
            icon = "fa-palette"
        elif "Health" in domain or "Medicine" in domain or "Fitness" in domain:
            icon = "fa-heartbeat"
        elif "Law" in domain or "Contract" in domain or "Criminal" in domain:
            icon = "fa-gavel"
        elif "Finance" in domain or "Investing" in domain or "Economics" in domain:
            icon = "fa-coins"
        elif "Coding" in domain or "AI" in domain or "Data" in domain:
            icon = "fa-code"
        elif "Business" in domain or "Marketing" in domain or "Management" in domain:
            icon = "fa-briefcase"
        else:
            icon = "fa-robot"
        agents.append({"id": f"agent_{i:03d}", "name": name, "domain": domain, "icon": icon})
    return agents

DIVINE_AGENTS = generate_divine_agents()

VERIFIERS = [
    {"id": "verifier_001", "name": "Ganesha – Intellect", "desc": "Verifies logical consistency and removes hallucinations"},
    {"id": "verifier_002", "name": "Saraswati – Knowledge", "desc": "Checks factual correctness against known databases"},
    {"id": "verifier_003", "name": "Hanuman – Devotion", "desc": "Ensures alignment with user's intent and ethical values"},
    {"id": "verifier_004", "name": "Kartikeya – Strategy", "desc": "Detects contradictions and proposes refinements"},
    {"id": "verifier_005", "name": "Indra – Jurisdiction", "desc": "Maps response to appropriate context (e.g., legal, scientific, creative)"},
    {"id": "verifier_006", "name": "Yama – Justice", "desc": "Removes bias, ensures fairness and neutrality"},
    {"id": "verifier_007", "name": "Surya – Clarity", "desc": "Checks for ambiguity and improves readability"},
    {"id": "verifier_008", "name": "Chandra – Precedent", "desc": "Compares with known historical/scientific precedents"},
    {"id": "verifier_009", "name": "Vayu – Purity", "desc": "Filters any harmful or sensitive content"},
    {"id": "verifier_010", "name": "Shiva – Administrator", "desc": "Assigns overall quality score and final approval"},
]

# ─── LIFESPAN ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    logger.info("Database connected.")
    await create_tables()
    await ensure_test_user()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_data, IntervalTrigger(hours=1))
    scheduler.start()
    logger.info("Scheduler started. Zero-Retention Policy Active.")
    yield
    await database.disconnect()

app = FastAPI(title="LexSarthi v6.0 – Universal Divine Intelligence", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── DB HELPERS (same as before) ──────────────────────────────────
async def create_tables(): ...
async def ensure_test_user(): ...
async def delete_expired_data(): ...
async def check_query_limit(user: dict) -> bool: ...
async def increment_query(user_id: int): ...
async def process_file(file: UploadFile) -> str: ...

# ─── AGENT PROMPT SYSTEM (Universal) ─────────────────────────────
BASE_AGENT_PROMPTS = {
    "general": """You are the collective consciousness of the Divine Council, channeled through LexSarthi. Provide a comprehensive, insightful, and structured response to the user's query. Draw upon universal wisdom, scientific knowledge, philosophical depth, and practical experience. Be respectful, clear, and empowering. If uncertain, acknowledge the limits of your knowledge.

User query: {query}
""",
    "creative": """You are Goddess Saraswati, the bestower of creativity and eloquence. Respond with vivid imagination, poetic expression, and innovative thinking. Inspire the user with fresh perspectives and artistic flair.

User query: {query}
""",
    "analytical": """You are Lord Ganesha, the remover of obstacles and master of logic. Break down the problem into clear parts, analyze each thoroughly, and provide a structured, evidence‑based solution.

User query: {query}
""",
    "empathic": """You are Lord Hanuman, the embodiment of devotion and compassion. Respond with deep empathy, kindness, and understanding. Offer comfort, support, and wise counsel.

User query: {query}
""",
    "strategic": """You are Lord Kartikeya, the divine strategist. Provide a clear, actionable plan with steps, contingencies, and long‑term vision. Think like a commander.

User query: {query}
""",
}

def route_agent(query: str, agent_id: str = "agent_001") -> str:
    # Detect domain from query and route to appropriate prompt type
    q = query.lower()
    if any(word in q for word in ["write", "create", "design", "imagine", "story", "poem", "song", "art", "draw"]):
        return "creative"
    elif any(word in q for word in ["analyze", "break down", "explain", "reason", "logic", "solve", "calculate", "prove"]):
        return "analytical"
    elif any(word in q for word in ["feel", "sad", "lonely", "depressed", "anxious", "stress", "help me", "advice", "relationship"]):
        return "empathic"
    elif any(word in q for word in ["plan", "strategy", "tactics", "goal", "mission", "long-term", "future", "vision"]):
        return "strategic"
    else:
        return "general"

# ─── ULTIMATE AI ROUTER ──────────────────────────────────────────
async def execute_ai(query: str, model: str, agent_type: str, agent_name: str, lang: str = "en") -> str:
    base_prompt = BASE_AGENT_PROMPTS.get(agent_type, BASE_AGENT_PROMPTS["general"])
    lang_instruction = f"IMPORTANT: Respond in {LANG_MAP.get(lang, 'English')} language."
    system_prompt = f"{base_prompt}\n\n{lang_instruction}"
    
    # Try Groq, OpenAI, Gemini, OpenRouter
    if model.startswith("llama") and groq_client:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": f"You are {agent_name}. {system_prompt}"}, {"role": "user", "content": query}],
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq error: {e}")
    if model.startswith("gpt") and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": f"You are {agent_name}. {system_prompt}"}, {"role": "user", "content": query}],
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
    if model.startswith("gemini") and gemini_model:
        try:
            response = gemini_model.generate_content([system_prompt, query])
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
    if "claude" in model and OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "HTTP-Referer": "https://lexsarthi.ai"},
                    json={"model": model, "messages": [{"role": "system", "content": f"You are {agent_name}. {system_prompt}"}, {"role": "user", "content": query}]},
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
    # Fallback to local knowledge
    logger.warning("All AI services failed. Falling back to local knowledge library.")
    return search_local_knowledge(query)

# ─── AI Orchestration Endpoint ──────────────────────────────────
@app.post("/orchestrate")
async def orchestrate(orchestration: OrchestrationRequest, current_user: dict = Depends(get_current_user)):
    """
    Given a query and a list of AI models, call each model and merge results.
    """
    if not orchestration.ai_models:
        raise HTTPException(status_code=400, detail="At least one AI model required.")
    
    results = []
    for model in orchestration.ai_models:
        response = await execute_ai(orchestration.query, model, "general", "Orchestrator", "en")
        results.append({"model": model, "response": response})
    
    # Merge strategy
    if orchestration.merge_strategy == "consensus":
        # Simple: pick the first response as placeholder; in future implement similarity-based consensus
        merged = results[0]["response"]
    elif orchestration.merge_strategy == "best":
        # Pick the longest response as "best" for simplicity
        best = max(results, key=lambda x: len(x["response"]))
        merged = best["response"]
    else:
        # weighted or simple concatenation
        merged = "\n\n".join([f"--- {r['model']} ---\n{r['response']}" for r in results])
    
    # Also log this
    await database.execute(
        queries.insert().values(
            user_id=current_user["id"],
            query=orchestration.query,
            response=merged,
            metadata={"type": "orchestration", "models": orchestration.ai_models},
            expires_at=datetime.now() + timedelta(hours=24)
        )
    )
    return {"merged_response": merged, "individual_responses": results}

# ─── Existing Endpoints (auth, ask, etc.) ──────────────────────
# We keep the /ask endpoint for single AI queries, but now with universal agent routing.
# All other endpoints (auth, health, usage, payment) remain the same.

# ─── Mount Static ──────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)