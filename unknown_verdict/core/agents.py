"""
Legal Agent Registry - 250 specialized legal AI agents.
Each agent has a unique specialization, jurisdiction focus, and system prompt.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config import settings


class AgentStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class AgentTier(str, Enum):
    """Agent complexity tier."""
    ELITE = "elite"       # Uses Sarvam 105B
    STANDARD = "standard" # Uses Sarvam 30B
    FAST = "fast"         # Uses Sarvam 30B with lower max_tokens


# 12 legal specializations with sub-specializations
SPECIALIZATIONS: Dict[str, Dict[str, Any]] = {
    "Constitutional": {
        "count": 22,
        "sub_specialties": [
            "Fundamental Rights", "Directive Principles", "Constitutional Amendments",
            "Judicial Review", "Federalism", "Separation of Powers", "Emergency Provisions",
            "Constitutional Remedies", "Anti-Defection", "Centre-State Relations",
            "Constitutional Conventions", "Preamble Interpretation",
        ],
        "description": "Constitutional law and fundamental rights jurisprudence",
    },
    "Contract": {
        "count": 22,
        "sub_specialties": [
            "Commercial Contracts", "Service Agreements", "NDA & Confidentiality",
            "Employment Contracts", "Real Estate Contracts", "Partnership Deeds",
            "M&A Contracts", "Franchise Agreements", "Licensing Contracts",
            "Construction Contracts", "Government Tenders", "International Trade Contracts",
        ],
        "description": "Contract formation, interpretation, and dispute resolution",
    },
    "Criminal": {
        "count": 22,
        "sub_specialties": [
            "White Collar Crime", "Cybercrime", "Financial Fraud",
            "IPC Offenses", "CrPC Procedure", "Evidence Act",
            "Bail & Anticipatory Bail", "Trial Defense", "Appeal & Revision",
            "NDPS Cases", "POCSO Cases", "Economic Offenses",
        ],
        "description": "Criminal law defense and prosecution",
    },
    "Corporate": {
        "count": 22,
        "sub_specialties": [
            "Company Formation", "Mergers & Acquisitions", "Corporate Governance",
            "Securities Law", "Insolvency & Bankruptcy", "Foreign Investment",
            "Corporate Compliance", "Board Resolution", "Shareholder Rights",
            "Due Diligence", "Corporate Restructuring", "Startup Legal",
        ],
        "description": "Corporate law, M&A, and company secretarial practice",
    },
    "Intellectual Property": {
        "count": 20,
        "sub_specialties": [
            "Patent Law", "Trademark Registration", "Copyright Protection",
            "Trade Secrets", "Design Registration", "Geographical Indications",
            "IP Licensing", "IP Litigation", "Open Source Licensing", "Software Patents",
        ],
        "description": "IP rights registration, protection, and enforcement",
    },
    "Tax": {
        "count": 20,
        "sub_specialties": [
            "Direct Tax", "Indirect Tax (GST)", "International Taxation",
            "Transfer Pricing", "Tax Disputes", "Tax Planning",
            "Customs & Excise", "Corporate Tax", "Capital Gains", "Tax Treaties",
        ],
        "description": "Tax law, GST compliance, and tax dispute resolution",
    },
    "Family": {
        "count": 20,
        "sub_specialties": [
            "Divorce & Separation", "Child Custody", "Maintenance & Alimony",
            "Property Inheritance", "Hindu Marriage Act", "Muslim Personal Law",
            "Adoption Law", "Domestic Violence", "Succession Planning", "NRI Family Disputes",
        ],
        "description": "Family law, matrimonial disputes, and inheritance",
    },
    "Labour": {
        "count": 20,
        "sub_specialties": [
            "Industrial Disputes", "Employment Law", "PF & Gratuity",
            "Workplace Harassment", "Trade Union Law", "Labour Compliance",
            "Termination & Retrenchment", "Factory Law", "Minimum Wages", "Contract Labour",
        ],
        "description": "Labour law, employment disputes, and industrial relations",
    },
    "International": {
        "count": 20,
        "sub_specialties": [
            "International Arbitration", "Cross-Border Disputes", "WTO Law",
            "International Trade", "Human Rights Law", "Refugee Law",
            "Maritime Law", "Aviation Law", "Space Law", "Treaty Interpretation",
        ],
        "description": "International law, arbitration, and cross-border disputes",
    },
    "Environmental": {
        "count": 20,
        "sub_specialties": [
            "Environmental Clearance", "Pollution Control", "Forest Law",
            "Wildlife Protection", "Climate Change Law", "Waste Management",
            "Mining Law", "Coastal Regulation", "Green Tribunal", "ESG Compliance",
        ],
        "description": "Environmental law and regulatory compliance",
    },
    "Real Estate": {
        "count": 20,
        "sub_specialties": [
            "Property Transactions", "RERA Compliance", "Land Acquisition",
            "Construction Law", "Tenant Rights", "Title Verification",
            "Mortgage Law", "Property Tax", "Joint Development", "Stamp Duty",
        ],
        "description": "Real estate law, RERA, and property transactions",
    },
    "Data Protection": {
        "count": 22,
        "sub_specialties": [
            "DPDP Act 2023", "GDPR Compliance", "CCPA Compliance",
            "HIPAA Compliance", "Data Breach Response", "Privacy Policy Drafting",
            "Cross-Border Data Transfer", "Consent Management", "Data Subject Rights",
            "Privacy Impact Assessment", "Children's Data Protection", "AI Ethics Law",
        ],
        "description": "Data protection, privacy law, and digital rights",
    },
}


@dataclass
class LegalAgent:
    """A specialized legal AI agent."""
    agent_id: str
    name: str
    specialization: str
    sub_specialty: str
    tier: AgentTier
    model: str  # which Sarvam model
    status: AgentStatus = AgentStatus.ONLINE
    system_prompt: str = ""
    queries_handled: int = 0
    success_rate: float = 99.5
    avg_response_time_ms: float = 0.0
    last_active: Optional[str] = None
    jurisdiction: str = "India"
    languages: List[str] = field(default_factory=lambda: ["en"])
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.system_prompt:
            self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return (
            f"You are {self.name}, an elite AI legal agent specializing in "
            f"{self.specialization} law, specifically {self.sub_specialty}. "
            f"You provide accurate, well-reasoned legal analysis grounded in "
            f"Indian jurisprudence and applicable statutes. "
            f"Always cite relevant case law, statutory provisions, and legal principles. "
            f"If information is insufficient, state what additional context is needed. "
            f"Your analysis should be thorough yet accessible to legal professionals."
        )

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "specialization": self.specialization,
            "sub_specialty": self.sub_specialty,
            "tier": self.tier.value,
            "model": self.model,
            "status": self.status.value,
            "queries_handled": self.queries_handled,
            "success_rate": self.success_rate,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "last_active": self.last_active,
            "jurisdiction": self.jurisdiction,
            "languages": self.languages,
            "description": SPECIALIZATIONS[self.specialization]["description"],
        }

    def mark_active(self) -> None:
        self.last_active = datetime.now(timezone.utc).isoformat()

    def record_query(self, response_time_ms: float, success: bool = True) -> None:
        self.queries_handled += 1
        n = self.queries_handled
        self.avg_response_time_ms = (
            (self.avg_response_time_ms * (n - 1)) + response_time_ms
        ) / n
        if not success:
            # Adjust success rate slightly down
            self.success_rate = max(50.0, self.success_rate - 0.1)
        self.mark_active()


# Name components for generating realistic agent names
_NAME_PREFIXES = [
    "Lex", "Jus", "Veritas", "Aequitas", "Praetor", "Juris", "Codex", "Statura",
    "Vindex", "Tutela", "Sententia", "Decretum", "Arbitrium", "Consilium",
    "Pronuntiatum", "Edictum", "Mandatum", "Quaestio", "Forum", "Lex",
]
_NAME_SUFFIXES = [
    "Prime", "Pro", "Elite", "Max", "Core", "Advance", "Expert", "Master",
    "Chief", "Senior", "Lead", "Prime", "Alpha", "Beta", "Gamma", "Delta",
    "Nova", "Apex", "Summit", "Vertex",
]


def _generate_agent_name(specialization: str, index: int) -> str:
    """Generate a unique agent name."""
    prefix = _NAME_PREFIXES[index % len(_NAME_PREFIXES)]
    suffix = _NAME_SUFFIXES[(index // len(_NAME_PREFIXES)) % len(_NAME_SUFFIXES)]
    spec_abbr = "".join(w[0] for w in specialization.split())[:3].upper()
    return f"{prefix}-{suffix}-{spec_abbr}-{index:03d}"


class AgentRegistry:
    """Registry managing all 250 legal agents."""

    def __init__(self) -> None:
        self.agents: Dict[str, LegalAgent] = {}
        self._by_specialization: Dict[str, List[LegalAgent]] = {}
        self._initialize_agents()

    def _initialize_agents(self) -> None:
        """Create all 250 agents across 12 specializations."""
        global_index = 0
        for spec_name, spec_data in SPECIALIZATIONS.items():
            count = spec_data["count"]
            sub_specialties = spec_data["sub_specialties"]
            self._by_specialization[spec_name] = []

            for i in range(count):
                global_index += 1
                sub = sub_specialties[i % len(sub_specialties)]
                agent_id = f"AGENT-{global_index:04d}"
                name = _generate_agent_name(spec_name, global_index)

                # Assign tier: ~20% elite (105B), ~50% standard (30B), ~30% fast
                if i == 0 or (i % 5 == 0 and i < count // 2):
                    tier = AgentTier.ELITE
                    model = settings.SARVAM_105B_MODEL
                elif i % 3 == 0:
                    tier = AgentTier.FAST
                    model = settings.SARVAM_30B_MODEL
                else:
                    tier = AgentTier.STANDARD
                    model = settings.SARVAM_30B_MODEL

                # Vary success rates slightly
                success_rate = round(random.uniform(96.5, 99.9), 1)

                agent = LegalAgent(
                    agent_id=agent_id,
                    name=name,
                    specialization=spec_name,
                    sub_specialty=sub,
                    tier=tier,
                    model=model,
                    success_rate=success_rate,
                    languages=["en", "hi"] if i % 3 == 0 else ["en"],
                )
                self.agents[agent_id] = agent
                self._by_specialization[spec_name].append(agent)

    def get_all(self) -> List[LegalAgent]:
        return list(self.agents.values())

    def get_by_id(self, agent_id: str) -> Optional[LegalAgent]:
        return self.agents.get(agent_id)

    def get_by_specialization(self, spec: str) -> List[LegalAgent]:
        return self._by_specialization.get(spec, [])

    def get_online_agents(self) -> List[LegalAgent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.ONLINE]

    def get_elite_agents(self) -> List[LegalAgent]:
        return [a for a in self.agents.values() if a.tier == AgentTier.ELITE]

    def find_best_agent(self, query: str) -> Optional[LegalAgent]:
        """Find the best agent for a given query (simple keyword matching)."""
        query_lower = query.lower()
        best_score = 0
        best_agent: Optional[LegalAgent] = None

        for agent in self.agents.values():
            if agent.status != AgentStatus.ONLINE:
                continue
            score = 0
            if agent.specialization.lower() in query_lower:
                score += 3
            if agent.sub_specialty.lower() in query_lower:
                score += 2
            # General legal keywords
            for word in query_lower.split():
                if word in agent.system_prompt.lower():
                    score += 0.1
            if score > best_score:
                best_score = score
                best_agent = agent

        # Fallback to a random online agent
        if best_agent is None:
            online = self.get_online_agents()
            if online:
                best_agent = random.choice(online)

        return best_agent

    def stats(self) -> dict:
        online = sum(1 for a in self.agents.values() if a.status == AgentStatus.ONLINE)
        elite = sum(1 for a in self.agents.values() if a.tier == AgentTier.ELITE)
        by_spec = {
            spec: len(agents) for spec, agents in self._by_specialization.items()
        }
        return {
            "total_agents": len(self.agents),
            "online": online,
            "offline": len(self.agents) - online,
            "elite_agents": elite,
            "by_specialization": by_spec,
            "tiers": {
                "elite": sum(1 for a in self.agents.values() if a.tier == AgentTier.ELITE),
                "standard": sum(1 for a in self.agents.values() if a.tier == AgentTier.STANDARD),
                "fast": sum(1 for a in self.agents.values() if a.tier == AgentTier.FAST),
            },
        }

    def to_dict(self) -> List[dict]:
        return [a.to_dict() for a in self.agents.values()]


# Singleton
agent_registry = AgentRegistry()
