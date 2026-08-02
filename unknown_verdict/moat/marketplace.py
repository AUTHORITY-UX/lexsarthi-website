"""Features 17 & 18: Legal Marketplace + AI Agent Marketplace."""
from __future__ import annotations
from typing import Any, Dict, List
from .db import db

class Marketplace:
    async def create_listing(self, listing_type: str, title: str, description: str,
                             price_inr: int, creator_id: str, metadata: Dict = None) -> Dict:
        lid = await db.add_listing(listing_type, title, description, price_inr, creator_id, metadata)
        return {"listing_id":lid or "","status":"active","listing_type":listing_type}

    async def list_agents(self) -> List[Dict]:
        rows = await db.fetch("SELECT * FROM moat_marketplace_listings WHERE listing_type='agent' AND status='active' ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in rows]

    async def list_templates(self) -> List[Dict]:
        rows = await db.fetch("SELECT * FROM moat_marketplace_listings WHERE listing_type='template' AND status='active' ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in rows]

    async def search(self, query: str) -> List[Dict]:
        rows = await db.fetch("SELECT * FROM moat_marketplace_listings WHERE status='active' AND (title ILIKE $1 OR description ILIKE $1) ORDER BY created_at DESC LIMIT 20", f"%{query}%")
        return [dict(r) for r in rows]

    async def client_lawyer_match(self, case_type: str, budget_inr: int = 0) -> Dict[str, Any]:
        # Match based on agent specialty
        try:
            from ..core import agent_registry
            agents = agent_registry.get_all() if hasattr(agent_registry, "get_all") else []
            matches = []
            for a in agents[:10]:
                spec = getattr(a, "specialization", "") or str(getattr(a, "persona", {}).get("specialization", "")) if hasattr(a, "persona") and isinstance(a.persona, dict) else ""
                if case_type.lower() in str(spec).lower():
                    matches.append({"agent_id":getattr(a,"id",""),"name":getattr(a,"name",""),
                                    "specialization":spec,"estimated_fee":budget_inr or 50000})
            return {"case_type":case_type,"matches":matches[:5],"total_matches":len(matches)}
        except Exception:
            return {"case_type":case_type,"matches":[],"note":"Agent registry not available for matching"}

marketplace = Marketplace()
