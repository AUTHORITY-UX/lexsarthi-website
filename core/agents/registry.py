# 500 Agents – Complete Registry

AGENTS = {
    # ─── LEGAL RESEARCH (100) ───
    "legal_001": {"name": "Constitutional Law Expert", "category": "Legal Research", "jurisdiction": "india"},
    "legal_002": {"name": "Criminal Law Specialist", "category": "Legal Research", "jurisdiction": "india"},
    "legal_003": {"name": "Civil Law Analyst", "category": "Legal Research", "jurisdiction": "india"},
    "legal_004": {"name": "Corporate Law Advisor", "category": "Legal Research", "jurisdiction": "india"},
    "legal_005": {"name": "Family Law Consultant", "category": "Legal Research", "jurisdiction": "india"},
    "legal_006": {"name": "Property Law Expert", "category": "Legal Research", "jurisdiction": "india"},
    "legal_007": {"name": "Labour Law Specialist", "category": "Legal Research", "jurisdiction": "india"},
    "legal_008": {"name": "Tax Law Analyst", "category": "Legal Research", "jurisdiction": "india"},
    "legal_009": {"name": "IP Law Expert", "category": "Legal Research", "jurisdiction": "global"},
    "legal_010": {"name": "Cyber Law Specialist", "category": "Legal Research", "jurisdiction": "global"},
    "legal_011": {"name": "Environmental Law Expert", "category": "Legal Research", "jurisdiction": "global"},
    "legal_012": {"name": "Consumer Protection Lawyer", "category": "Legal Research", "jurisdiction": "india"},
    "legal_013": {"name": "Banking Law Analyst", "category": "Legal Research", "jurisdiction": "india"},
    "legal_014": {"name": "Immigration Law Expert", "category": "Legal Research", "jurisdiction": "global"},
    "legal_015": {"name": "International Law Specialist", "category": "Legal Research", "jurisdiction": "global"},
    # ... Continue to 100
    
    # ─── COMPLIANCE (80) ───
    "comp_001": {"name": "DPDPA Compliance Expert", "category": "Compliance", "jurisdiction": "india"},
    "comp_002": {"name": "GDPR Specialist", "category": "Compliance", "jurisdiction": "eu"},
    "comp_003": {"name": "EU AI Act Assessor", "category": "Compliance", "jurisdiction": "eu"},
    "comp_004": {"name": "CCPA/CPRA Analyst", "category": "Compliance", "jurisdiction": "us"},
    "comp_005": {"name": "UK Data Protection Expert", "category": "Compliance", "jurisdiction": "uk"},
    "comp_006": {"name": "Cross-Border Data Specialist", "category": "Compliance", "jurisdiction": "global"},
    "comp_007": {"name": "Regulatory Change Monitor", "category": "Compliance", "jurisdiction": "global"},
    # ... Continue to 80
    
    # ─── CONTRACTS (60) ───
    "contract_001": {"name": "NDA Reviewer", "category": "Contracts", "jurisdiction": "global"},
    "contract_002": {"name": "MSA Analyst", "category": "Contracts", "jurisdiction": "global"},
    "contract_003": {"name": "Employment Contract Expert", "category": "Contracts", "jurisdiction": "india"},
    "contract_004": {"name": "Vendor Contract Specialist", "category": "Contracts", "jurisdiction": "global"},
    "contract_005": {"name": "Lease Agreement Analyst", "category": "Contracts", "jurisdiction": "global"},
    "contract_006": {"name": "Partnership Agreement Expert", "category": "Contracts", "jurisdiction": "global"},
    # ... Continue to 60
    
    # ─── EMPLOYMENT & HR (40) ───
    "hr_001": {"name": "POSH Policy Auditor", "category": "Employment", "jurisdiction": "india"},
    "hr_002": {"name": "Workplace Safety Inspector", "category": "Employment", "jurisdiction": "india"},
    "hr_003": {"name": "Payroll Compliance Expert", "category": "Employment", "jurisdiction": "india"},
    "hr_004": {"name": "Employment Law Advisor", "category": "Employment", "jurisdiction": "global"},
    # ... Continue to 40
    
    # ─── TAX & FINANCE (40) ───
    "tax_001": {"name": "GST Compliance Expert", "category": "Tax", "jurisdiction": "india"},
    "tax_002": {"name": "Income Tax Specialist", "category": "Tax", "jurisdiction": "india"},
    "tax_003": {"name": "Transfer Pricing Analyst", "category": "Tax", "jurisdiction": "global"},
    "tax_004": {"name": "Financial Due Diligence Expert", "category": "Tax", "jurisdiction": "global"},
    # ... Continue to 40
    
    # ─── INTELLECTUAL PROPERTY (40) ───
    "ip_001": {"name": "Patent Examiner", "category": "IP", "jurisdiction": "global"},
    "ip_002": {"name": "Trademark Analyst", "category": "IP", "jurisdiction": "global"},
    "ip_003": {"name": "Copyright Specialist", "category": "IP", "jurisdiction": "global"},
    "ip_004": {"name": "Trade Secret Protector", "category": "IP", "jurisdiction": "global"},
    # ... Continue to 40
    
    # ─── AI & TECHNOLOGY (60) ───
    "ai_001": {"name": "AI Governance Auditor", "category": "AI", "jurisdiction": "global"},
    "ai_002": {"name": "Algorithmic Bias Detector", "category": "AI", "jurisdiction": "global"},
    "ai_003": {"name": "AI Growth Tracker", "category": "AI", "jurisdiction": "global"},
    "ai_004": {"name": "Physical AI Monitor", "category": "AI", "jurisdiction": "global"},
    "ai_005": {"name": "AI IP Expert", "category": "AI", "jurisdiction": "global"},
    # ... Continue to 60
    
    # ─── DIGITAL INTELLIGENCE (40) ───
    "digital_001": {"name": "Domain Scanner", "category": "Digital", "jurisdiction": "global"},
    "digital_002": {"name": "Dark Web Monitor", "category": "Digital", "jurisdiction": "global"},
    "digital_003": {"name": "Website Compliance Analyst", "category": "Digital", "jurisdiction": "global"},
    "digital_004": {"name": "Digital Reputation Expert", "category": "Digital", "jurisdiction": "global"},
    # ... Continue to 40
    
    # ─── LITIGATION (30) ───
    "lit_001": {"name": "Case Outcome Predictor", "category": "Litigation", "jurisdiction": "india"},
    "lit_002": {"name": "Arbitration Expert", "category": "Litigation", "jurisdiction": "global"},
    "lit_003": {"name": "Mediation Specialist", "category": "Litigation", "jurisdiction": "global"},
    "lit_004": {"name": "E-Discovery Expert", "category": "Litigation", "jurisdiction": "global"},
    # ... Continue to 30
    
    # ─── STRATEGIC ADVISORY (10) ───
    "strat_001": {"name": "M&A Due Diligence Expert", "category": "Strategic", "jurisdiction": "global"},
    "strat_002": {"name": "IPO Readiness Advisor", "category": "Strategic", "jurisdiction": "india"},
    "strat_003": {"name": "Succession Planning Expert", "category": "Strategic", "jurisdiction": "global"},
    "strat_004": {"name": "Corporate Strategy Consultant", "category": "Strategic", "jurisdiction": "global"},
    # ... Continue to 10
}

def get_agent(agent_id: str):
    return AGENTS.get(agent_id)

def get_agents_by_category(category: str):
    return {k: v for k, v in AGENTS.items() if v["category"] == category}

def get_all_agents():
    return AGENTS

def get_agent_categories():
    categories = {}
    for agent in AGENTS.values():
        cat = agent["category"]
        categories[cat] = categories.get(cat, 0) + 1
    return categories
# ─── ADD THESE FUNCTIONS ──────────────────────────────────────────

def get_agents_by_jurisdiction(jurisdiction: str):
    """Get agents filtered by jurisdiction"""
    jurisdiction = jurisdiction.lower()
    result = {}
    for agent_id, agent in AGENTS.items():
        if agent.get("jurisdiction", "").lower() == jurisdiction:
            result[agent_id] = agent
    return result

def search_agents(query: str):
    """Search agents by name, category, or specialty"""
    query = query.lower()
    results = []
    for agent in AGENTS.values():
        name = agent.get("name", "").lower()
        category = agent.get("category", "").lower()
        specialty = agent.get("specialty", "").lower()
        if query in name or query in category or query in specialty:
            results.append(agent)
    return results[:20]

def get_agent_stats():
    """Get statistics about all agents"""
    categories = {}
    jurisdictions = {
        "india": 0,
        "us": 0,
        "uk": 0,
        "eu": 0,
        "global": 0
    }
    
    for agent in AGENTS.values():
        cat = agent.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1
        
        jur = agent.get("jurisdiction", "global").lower()
        if jur in jurisdictions:
            jurisdictions[jur] += 1
        else:
            jurisdictions["global"] += 1
    
    return {
        "total": len(AGENTS),
        "categories": categories,
        "jurisdictions": jurisdictions,
        "timestamp": datetime.now().isoformat()
    }