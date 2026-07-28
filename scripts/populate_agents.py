#!/usr/bin/env python3
# populate_agents.py - Generate 3000 Agents in PostgreSQL Database
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncio
import os
import sys
import random
import logging
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("populate_agents")

# ─── DATABASE CONNECTION ──────────────────────────────────────────────

import asyncpg
from sentence_transformers import SentenceTransformer
import numpy as np

# ─── AGENT DATA ──────────────────────────────────────────────────────

# 60+ Legal Domains
LEGAL_DOMAINS = [
    # Constitutional & Public Law
    "Constitutional Law", "Administrative Law", "Public International Law",
    "Human Rights Law", "Environmental Law", "Energy Law",
    
    # Private Law
    "Contract Law", "Tort Law", "Property Law", "Family Law",
    "Succession Law", "Trust Law",
    
    # Commercial & Corporate
    "Corporate Law", "Mergers & Acquisitions", "Securities Law",
    "Banking Law", "Insurance Law", "Insolvency Law",
    "Competition Law", "Consumer Protection Law",
    
    # Criminal Law
    "Criminal Law", "Criminal Procedure", "Evidence Law",
    "Cyber Crime Law", "White Collar Crime",
    
    # Tax Law
    "Income Tax Law", "GST Law", "Customs Law", "International Tax Law",
    
    # IP & Technology
    "Intellectual Property Law", "Patent Law", "Trademark Law",
    "Copyright Law", "Cyber Law", "Data Privacy Law",
    "AI Governance Law",
    
    # Labour & Employment
    "Labour Law", "Employment Law", "Industrial Relations Law",
    
    # Specialized
    "Arbitration Law", "ADR Law", "Maritime Law", "Space Law",
    "Sports Law", "Media Law", "Entertainment Law",
    "Education Law", "Healthcare Law", "Pharmaceutical Law",
    "Real Estate Law", "Construction Law", "Infrastructure Law",
    
    # International
    "International Trade Law", "WTO Law", "International Arbitration",
    "Conflict of Laws", "Diplomatic Law",
    
    # Regulatory
    "Regulatory Law", "Compliance Law", "Anti-Money Laundering",
    "Sanctions Law", "Export Control Law",
    
    # Emerging
    "Blockchain Law", "Cryptocurrency Law", "Fintech Law",
    "Biotech Law", "Genetics Law", "Nanotech Law",
]

# Spiritual & Philosophical Domains
SPIRITUAL_DOMAINS = [
    "Vedanta Philosophy", "Advaita Vedanta", "Dvaita Vedanta",
    "Buddhist Philosophy", "Jain Philosophy", "Sikh Philosophy",
    "Yoga Philosophy", "Meditation Science", "Mindfulness",
    "Bhagavad Gita", "Upanishads", "Ramayana", "Mahabharata",
    "Ayurveda", "Sanskrit Literature", "Indian Mythology",
    "Ethics", "Moral Philosophy", "Political Philosophy",
    "Cognitive Science", "Neuroscience", "Psychology",
    "Consciousness Studies", "Transcendental Meditation",
]

# Scientific & Mathematical Domains
SCIENTIFIC_DOMAINS = [
    # Physics
    "Quantum Mechanics", "Relativity", "Thermodynamics",
    "Electromagnetism", "Optics", "Acoustics", "Plasma Physics",
    "Astrophysics", "Cosmology", "Particle Physics",
    "Nuclear Physics", "Condensed Matter Physics",
    
    # Chemistry
    "Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry",
    "Biochemistry", "Analytical Chemistry", "Environmental Chemistry",
    
    # Biology
    "Genetics", "Evolutionary Biology", "Cell Biology",
    "Molecular Biology", "Ecology", "Marine Biology",
    "Microbiology", "Botany", "Zoology", "Neuroscience",
    
    # Mathematics
    "Pure Mathematics", "Applied Mathematics", "Algebra",
    "Calculus", "Geometry", "Topology", "Number Theory",
    "Statistics", "Probability Theory",
    
    # Computer Science
    "Machine Learning", "Deep Learning", "Neural Networks",
    "Natural Language Processing", "Computer Vision",
    "Cryptography", "Blockchain", "Quantum Computing",
    "Algorithms", "Data Science", "Artificial Intelligence",
    
    # Earth Sciences
    "Geology", "Oceanography", "Meteorology", "Climatology",
    "Environmental Science", "Geography",
    
    # Medicine
    "Cardiology", "Neurology", "Oncology", "Radiology",
    "Surgery", "Internal Medicine", "Pediatrics",
    "Psychiatry", "Dermatology", "Orthopedics",
]

# All domains combined
ALL_DOMAINS = LEGAL_DOMAINS + SPIRITUAL_DOMAINS + SCIENTIFIC_DOMAINS

# Jurisdictions
JURISDICTIONS = ["IN", "US", "UK", "EU", "CA", "AU", "SG", "AE", "ZA", "BR"]

# Experience Levels
EXPERIENCE_LEVELS = ["junior", "mid", "senior", "expert"]

# Divine Names for Agent Personalities
DIVINE_NAMES = [
    "Brahma", "Vishnu", "Shiva", "Saraswati", "Lakshmi", "Ganesha",
    "Hanuman", "Kartikeya", "Indra", "Yama", "Surya", "Chandra",
    "Vayu", "Agni", "Varuna", "Kubera", "Yamuna", "Ganga",
    "Durga", "Kali", "Tara", "Bhuvaneshwari", "Chinnamasta",
    "Bhairavi", "Dhumavati", "Bagalamukhi", "Matangi", "Kamala",
    "Dattatreya", "Narasimha", "Vamana", "Parashurama", "Rama",
    "Krishna", "Buddha", "Kalki", "Matsya", "Kurma", "Varaha",
    "Skanda", "Ayyappa", "Shani", "Mangal", "Budh", "Guru",
    "Shukra", "Rahu", "Ketu", "Vishvakarma", "Savitr", "Pushan",
    "Ashwini", "Shraddha", "Medha", "Dhi", "Prajna", "Smriti"
]

# Category mapping
CATEGORY_MAP = {
    "legal": "legal",
    "spiritual": "spiritual", 
    "scientific": "scientific"
}

# ─── STATUTES BY DOMAIN ─────────────────────────────────────────────

STATUTES_MAP = {
    "Constitutional Law": ["Constitution of India", "Article 14-32", "Article 368"],
    "Contract Law": ["Indian Contract Act 1872", "Sections 1-75", "Specific Relief Act"],
    "Criminal Law": ["Indian Penal Code 1860", "CrPC 1973", "Evidence Act 1872"],
    "Corporate Law": ["Companies Act 2013", "SEBI Act 1992", "Insolvency Code 2016"],
    "Tax Law": ["Income Tax Act 1961", "GST Act 2017", "Finance Act"],
    "IP Law": ["Patents Act 1970", "Trademarks Act 1999", "Copyright Act 1957"],
    "Family Law": ["Hindu Marriage Act 1955", "Muslim Personal Law", "Special Marriage Act"],
    "Labour Law": ["Industrial Disputes Act 1947", "Factories Act 1948", "Minimum Wages Act"],
    "Environmental Law": ["Environment Protection Act 1986", "Forest Act 1927", "Wildlife Act"],
    "Cyber Law": ["IT Act 2000", "DPDP Act 2023", "Rules & Regulations"],
}

# ─── KEY SECTIONS BY DOMAIN ─────────────────────────────────────────

KEY_SECTIONS_MAP = {
    "Constitutional Law": ["Art 14", "Art 15", "Art 21", "Art 32", "Art 226"],
    "Contract Law": ["Sec 10", "Sec 23", "Sec 56", "Sec 73", "Sec 124"],
    "Criminal Law": ["Sec 299", "Sec 300", "Sec 302", "Sec 304", "Sec 375", "Sec 377"],
    "Corporate Law": ["Sec 149", "Sec 166", "Sec 184", "Sec 185", "Sec 186"],
    "Tax Law": ["Sec 2", "Sec 4", "Sec 10", "Sec 14", "Sec 22", "Sec 28"],
    "IP Law": ["Sec 2", "Sec 3", "Sec 11", "Sec 18", "Sec 21"],
}

# ─── PERSONA PROMPTS ────────────────────────────────────────────────

def generate_persona_prompt(domain: str, category: str, jurisdiction: str, experience: str) -> str:
    """Generate a detailed persona prompt for each agent."""
    
    experience_desc = {
        "junior": "You are a junior specialist with foundational knowledge. Focus on basic principles and seeking guidance.",
        "mid": "You are a mid-level specialist with practical experience. Provide balanced, actionable advice.",
        "senior": "You are a senior specialist with deep expertise. Provide strategic, nuanced analysis.",
        "expert": "You are a renowned expert in your field. Provide authoritative, cutting-edge insights."
    }
    
    base = f"You are {experience_desc.get(experience, 'a specialist')} in {domain}. "
    
    if category == "legal":
        base += f"You practice in {jurisdiction} jurisdiction. "
        base += "Provide legally sound, practical advice with proper citations. "
        base += "Always consider the client's best interests while maintaining professional ethics. "
    elif category == "spiritual":
        base += "You provide spiritual guidance and philosophical wisdom. "
        base += "Draw from ancient texts, traditions, and universal principles. "
        base += "Be compassionate, insightful, and transformative. "
    else:  # scientific
        base += "You provide rigorous, evidence-based scientific analysis. "
        base += "Use the scientific method, cite research, and admit uncertainty where it exists. "
        base += "Be precise, logical, and data-driven. "
    
    base += "Use deep expertise, think critically, and provide clear, actionable responses."
    
    return base

# ─── GENERATE AGENTS ────────────────────────────────────────────────

def generate_agents(count: int = 3000) -> List[Dict]:
    """Generate a list of agent dictionaries."""
    agents = []
    
    # Ensure we have enough domains
    domains = ALL_DOMAINS * (count // len(ALL_DOMAINS) + 1)
    
    for i in range(count):
        # Select domain cyclically
        domain = domains[i % len(domains)]
        
        # Determine category
        if domain in LEGAL_DOMAINS:
            category = "legal"
        elif domain in SPIRITUAL_DOMAINS:
            category = "spiritual"
        else:
            category = "scientific"
        
        # Random jurisdiction (weighted towards IN)
        jurisdiction = random.choices(
            JURISDICTIONS,
            weights=[50, 15, 10, 10, 5, 3, 3, 2, 1, 1],
            k=1
        )[0]
        
        # Experience level (weighted)
        experience = random.choices(
            EXPERIENCE_LEVELS,
            weights=[20, 35, 30, 15],
            k=1
        )[0]
        
        # Get statutes and key sections
        statutes = STATUTES_MAP.get(domain, ["General principles", "Relevant case law"])
        key_sections = KEY_SECTIONS_MAP.get(domain, ["Relevant provisions"])
        
        # Generate agent name
        name = f"{random.choice(DIVINE_NAMES)} · {domain}"
        
        # Generate persona prompt
        persona_prompt = generate_persona_prompt(domain, category, jurisdiction, experience)
        
        agent = {
            "name": name,
            "domain": domain,
            "category": category,
            "jurisdiction": jurisdiction,
            "experience_level": experience,
            "persona_prompt": persona_prompt,
            "key_sections": key_sections,
            "statutes": statutes,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        agents.append(agent)
    
    return agents

# ─── DATABASE OPERATIONS ─────────────────────────────────────────────

async def create_table_if_not_exists(conn):
    """Create agents table with pgvector extension."""
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT NOT NULL,
            category TEXT NOT NULL,
            jurisdiction TEXT DEFAULT 'IN',
            experience_level TEXT DEFAULT 'mid',
            persona_prompt TEXT NOT NULL,
            key_sections TEXT[] DEFAULT '{}',
            statutes TEXT[] DEFAULT '{}',
            embedding vector(384),
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_agents_embedding 
        ON agents USING ivfflat (embedding vector_cosine_ops)
    """)

async def insert_agents(conn, agents: List[Dict], encoder):
    """Insert agents with embeddings."""
    inserted = 0
    batch_size = 50
    
    for i in range(0, len(agents), batch_size):
        batch = agents[i:i+batch_size]
        for agent in batch:
            # Generate embedding
            text = f"{agent['domain']} {agent['persona_prompt'][:500]}"
            embedding = encoder.encode(text).tolist()
            
            await conn.execute("""
                INSERT INTO agents (
                    name, domain, category, jurisdiction, experience_level,
                    persona_prompt, key_sections, statutes, embedding, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, 
                agent['name'], 
                agent['domain'], 
                agent['category'],
                agent['jurisdiction'],
                agent['experience_level'],
                agent['persona_prompt'],
                agent['key_sections'],
                agent['statutes'],
                embedding,
                agent['status']
            )
            inserted += 1
        
        logger.info(f"📊 Inserted {inserted}/{len(agents)} agents")
        await asyncio.sleep(0.1)  # Small delay to not overload DB
    
    return inserted

# ─── MAIN ─────────────────────────────────────────────────────────────

async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("🚀 POPULATING 3000 AGENTS")
    logger.info("=" * 60)
    
    # Get database URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not set in environment")
        logger.info("💡 Set DATABASE_URL and try again")
        sys.exit(1)
    
    logger.info(f"📊 Database: {DATABASE_URL[:50]}...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("✅ Connected to database")
        
        # Create table
        await create_table_if_not_exists(conn)
        logger.info("✅ Table created/verified")
        
        # Count existing agents
        count = await conn.fetchval("SELECT COUNT(*) FROM agents")
        logger.info(f"📊 Existing agents: {count}")
        
        # Generate agents
        target_count = 3000
        if count >= target_count:
            logger.info(f"✅ Already have {count} agents (target: {target_count})")
            logger.info("💡 Run: DELETE FROM agents; to reset")
            await conn.close()
            return
        
        to_generate = target_count - count
        logger.info(f"🔄 Generating {to_generate} new agents...")
        
        agents = generate_agents(to_generate)
        logger.info(f"✅ Generated {len(agents)} agents")
        
        # Load sentence transformer
        logger.info("📚 Loading embedding model...")
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Model loaded")
        
        # Insert agents
        logger.info("💾 Inserting agents into database...")
        inserted = await insert_agents(conn, agents, encoder)
        logger.info(f"✅ Inserted {inserted} agents")
        
        # Verify
        new_count = await conn.fetchval("SELECT COUNT(*) FROM agents")
        logger.info(f"📊 Total agents now: {new_count}")
        
        # Show sample
        sample = await conn.fetch("SELECT id, name, domain, jurisdiction, experience_level FROM agents LIMIT 5")
        logger.info("📋 Sample agents:")
        for row in sample:
            logger.info(f"   ├─ {row['id']}: {row['name']} | {row['domain']} | {row['jurisdiction']} | {row['experience_level']}")
        
        logger.info("=" * 60)
        logger.info(f"✅ SUCCESS: {new_count} agents in database")
        logger.info("🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE")
        logger.info("⚖️ THE ADVOCACY – Global Law Firm")
        logger.info("=" * 60)
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())