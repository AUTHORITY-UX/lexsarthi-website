# agent_selector.py - Semantic selection with filters
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

from typing import List, Dict, Optional
import logging

from agent_registry import AgentRegistry

logger = logging.getLogger(__name__)

class AgentSelector:
    def __init__(self):
        self.registry = AgentRegistry()

    async def select_agents(
        self,
        query: str,
        jurisdiction: str = "IN",
        age_group: str = "adult",
        case_type: str = "general",
        top_k: int = 15
    ) -> List[Dict]:
        """Return top‑k agents matching the query context."""
        filters = {"jurisdiction": jurisdiction}
        # Optionally map age_group/case_type to category filter
        if case_type.lower() in ["contract", "corporate", "tax", "ip"]:
            filters["category"] = "legal"
        elif case_type.lower() in ["spiritual", "meditation"]:
            filters["category"] = "spiritual"
        # else leave unconstrained

        # Semantic search
        candidates = await self.registry.semantic_search(
            query=query,
            filters=filters,
            top_k=top_k * 2  # get more then filter by experience
        )
        # Prioritize senior agents for complex queries (word count > 10 words)
        if len(query.split()) > 10:
            candidates.sort(key=lambda x: 1 if x.get('experience_level') == 'senior' else 0, reverse=True)
        return candidates[:top_k]