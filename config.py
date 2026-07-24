# =============================================================================
# config.py - Configuration & Environment Variables
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================

import os
import logging
from datetime import timedelta

# ─── LOGGING ──────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ─── ENVIRONMENT ────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", None)
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24 * 7

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", None)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_USER_ID = os.getenv("LINKEDIN_USER_ID")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me")

# ─── AI NEWS FEEDS ──────────────────────────────────────────────────
AI_NEWS_FEEDS = [
    "https://arxiv.org/rss/cs.AI",
    "https://feeds.feedburner.com/TechnologyReview/AI",
    "https://deepmind.com/blog/feed.xml",
    "https://openai.com/blog/rss.xml",
    "https://ai.meta.com/blog/feed/",
    "https://www.analyticsvidhya.com/feed/",
    "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://www.theverge.com/rss/ai/index.xml",
    "https://www.ibm.com/blogs/research/feed/",
    "https://research.google/blog/feed/",
    "https://venturebeat.com/category/ai/feed/",
]

# ─── SYSTEM PROMPT ──────────────────────────────────────────────────
SYSTEM_BASE = """You are the Unknown Verdict Engine – an AI advisory OS with 250 specialist personas, 
a jury of 10 verifiers, and a final judge. You have access to a knowledge base and live web search. 
Always strive for accuracy, cite sources, and admit uncertainty. 
Default jurisdiction: India. Tone: professional, wise, neutral."""

# ─── DOMAINS & AGENTS ──────────────────────────────────────────────
DOMAINS_FULL = [
    "Constitutional Law", "Contract Law", "Criminal Law", "Corporate Law", "Tax Law",
    "IP Law", "Family Law", "Cyber Law", "Arbitration", "Property Law", "GST", "Income Tax",
    "Audit", "Incorporation", "Compliance", "Mathematics", "Statistics", "Physics", "Chemistry",
    "Biology", "Medicine", "Psychology", "Philosophy", "Logic", "Reasoning", "Economics",
    "Finance", "History", "Geopolitics", "Astronomy", "Vedanta", "Yoga", "Ayurveda", "Sanskrit",
    "Mythology", "Ethics", "AI Ethics", "Cryptography", "Blockchain", "Climate Science",
    "Environmental Law", "Human Rights", "International Law", "Maritime Law", "Space Law",
    "Data Privacy", "E-commerce", "Real Estate", "Banking", "Insurance"
]

DIVINE_NAMES_POOL = ["Brahma","Vishnu","Shiva","Saraswati","Lakshmi","Ganesha","Hanuman",
    "Kartikeya","Indra","Yama","Surya","Chandra","Vayu","Agni","Varuna","Kubera",
    "Yamuna","Ganga","Durga","Kali","Tara","Bhuvaneshwari","Chinnamasta","Bhairavi",
    "Dhumavati","Bagalamukhi","Matangi","Kamala","Dattatreya","Narasimha","Vamana",
    "Parashurama","Rama","Krishna","Buddha","Kalki","Matsya","Kurma","Varaha","Skanda",
    "Ayyappa","Shani","Mangal","Budh","Guru","Shukra","Rahu","Ketu"]

sub_specialties = {
    "Constitutional Law": ["Fundamental Rights", "Federalism", "Judicial Review", "Amendment", "Emergency"],
    "Contract Law": ["Formation", "Performance", "Breach", "Remedies", "Specific Relief"],
    "Criminal Law": ["IPC", "CrPC", "Evidence", "White Collar", "Sentencing"],
    "Corporate Law": ["M&A", "Board Governance", "Shareholder Rights", "Insolvency", "SEBI"],
    "Tax Law": ["Direct Tax", "Indirect Tax", "International Tax", "Transfer Pricing", "Tax Litigation"],
}

# ─── VERIFIERS ──────────────────────────────────────────────────────
VERIFIERS = [
    {"id":"v01","name":"Ganesha","role":"Citation & logic integrity","prompt":"Check legal citations and logical flow."},
    {"id":"v02","name":"Saraswati","role":"Knowledge cross-reference","prompt":"Verify facts against established knowledge."},
    {"id":"v03","name":"Hanuman","role":"Global compliance","prompt":"Ensure advice follows international norms."},
    {"id":"v04","name":"Kartikeya","role":"Contradiction detection","prompt":"Find internal contradictions."},
    {"id":"v05","name":"Indra","role":"Jurisdiction mapping","prompt":"Check jurisdiction assumptions."},
    {"id":"v06","name":"Yama","role":"Bias & neutrality","prompt":"Scan for bias."},
    {"id":"v07","name":"Surya","role":"Timeline & limitation","prompt":"Confirm statutes are current."},
    {"id":"v08","name":"Chandra","role":"Precedent match","prompt":"Check alignment with known precedents."},
    {"id":"v09","name":"Vayu","role":"PII / privacy filter","prompt":"Redact PII."},
    {"id":"v10","name":"Shakti","role":"Final judge & dharma seal","prompt":"Integrate all critiques and produce a final answer with a confidence rating."}
]

# ─── TEMPLATES ──────────────────────────────────────────────────────
TEMPLATES = {
    "demand_letter": {
        "name": "Demand Letter (Personal Injury)",
        "fields": [
            {"key": "client_name", "label": "Client Name", "type": "text"},
            {"key": "client_address", "label": "Client Address", "type": "text"},
            {"key": "date_of_accident", "label": "Date of Accident", "type": "date"},
            {"key": "at_fault_driver", "label": "At-Fault Driver", "type": "text"},
            {"key": "insurance_company", "label": "Insurance Company", "type": "text"},
            {"key": "claim_number", "label": "Claim Number", "type": "text"},
            {"key": "injuries", "label": "Injuries", "type": "text"},
            {"key": "medical_bills", "label": "Medical Bills ($)", "type": "number"},
            {"key": "lost_wages", "label": "Lost Wages ($)", "type": "number"},
        ],
        "prompt": """Draft a professional demand letter with: Client: {client_name}, Address: {client_address}, Date: {date_of_accident}, Driver: {at_fault_driver}, Insurance: {insurance_company}, Claim #: {claim_number}, Injuries: {injuries}, Medical: ${medical_bills}, Lost Wages: ${lost_wages}."""
    },
    "nda": {
        "name": "Mutual Non-Disclosure Agreement",
        "fields": [
            {"key": "party_a", "label": "Party A", "type": "text"},
            {"key": "party_b", "label": "Party B", "type": "text"},
            {"key": "purpose", "label": "Purpose of Disclosure", "type": "text"},
            {"key": "term", "label": "Term (months)", "type": "number"},
        ],
        "prompt": """Draft a Mutual NDA between {party_a} and {party_b} for {purpose}. Term: {term} months."""
    },
    "motion_to_modify": {
        "name": "Motion to Modify Custody",
        "fields": [
            {"key": "petitioner", "label": "Petitioner", "type": "text"},
            {"key": "respondent", "label": "Respondent", "type": "text"},
            {"key": "case_number", "label": "Case Number", "type": "text"},
            {"key": "court", "label": "Court", "type": "text"},
            {"key": "reason", "label": "Reason", "type": "text"},
            {"key": "child_name", "label": "Child Name", "type": "text"},
        ],
        "prompt": """Draft a Motion to Modify Custody for {petitioner} vs {respondent}, Case # {case_number} in {court}. Reason: {reason}. Child: {child_name}."""
    }
}