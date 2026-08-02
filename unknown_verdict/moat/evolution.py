"""Feature 1: Self-Evolving Agent System."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from loguru import logger as log
from .db import db
from .embeddings import embed

class EvolutionEngine:
    async def record_interaction(self, agent_id: str, query: str, response: str,
        outcome: str = "unknown", confidence_delta: float = 0.0, interaction_id: str = "") -> Dict[str, Any]:
        learning_text = f"Query: {query[:500]}\nResponse: {response[:1000]}\nOutcome: {outcome}"
        emb = await embed(learning_text)
        lid = await db.add_learning(agent_id, query, learning_text, outcome, confidence_delta,
                                     interaction_id, emb, share=(outcome=="success"))
        if lid: await db.audit("agent","learning_stored","learning",lid,{"agent_id":agent_id,"outcome":outcome})
        return {"learning_id": lid or "", "outcome": outcome, "vector_indexed": lid is not None}

    async def recall_learnings(self, query: str, top_k: int = 5, agent_id: Optional[str] = None) -> List[Dict]:
        qv = await embed(query)
        where = ""; params = ()
        if agent_id: where = "agent_id = $2"; params = (agent_id,)
        rows = await db.vector_search("moat_learnings","embedding",qv,top_k,where,params)
        return [{"learning":r.get("learning",""),"outcome":r.get("outcome","unknown"),
                 "similarity":round(r.get("similarity",0),4),"agent_id":r.get("agent_id","")} for r in rows]

    async def get_mesh_knowledge(self, query: str, top_k: int = 8) -> List[Dict]:
        qv = await embed(query)
        rows = await db.vector_search("moat_learnings","embedding",qv,top_k,"shared_to_mesh = TRUE")
        return [{"learning":r.get("learning",""),"agent_id":r.get("agent_id",""),
                 "outcome":r.get("outcome","unknown"),"similarity":round(r.get("similarity",0),4)} for r in rows]

    async def generate_training_data(self, agent_id: str, limit: int = 20) -> List[Dict]:
        rows = await db.fetch("SELECT * FROM moat_learnings WHERE agent_id=$1 AND outcome='success' ORDER BY created_at DESC LIMIT $2", agent_id, limit)
        pairs = []
        for r in rows:
            t = r.get("learning","") or ""
            if "Query:" in t and "Response:" in t:
                pairs.append({"instruction":t.split("Query:")[1].split("Response:")[0].strip(),
                              "output":t.split("Response:")[1].split("Outcome:")[0].strip(),
                              "agent_id":agent_id,"source":"self_generated"})
        return pairs

    async def detect_knowledge_gap(self, query: str, agent_id: str, confidence: float = 0.5) -> Optional[Dict]:
        qv = await embed(query)
        rows = await db.vector_search("moat_learnings","embedding",qv,top_k=3)
        max_sim = max((r.get("similarity",0) for r in rows), default=0.0)
        if max_sim < 0.40 and confidence < 0.6:
            spec = self._infer_specialty(query)
            slug = f"auto-{spec}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
            proposal = {"gap_detected":True,"query":query[:200],"max_similarity":round(max_sim,4),
                        "confidence":confidence,"proposed_agent_slug":slug,"proposed_specialty":spec}
            await db.audit("evolution","gap_detected","agent",agent_id,proposal)
            return proposal
        return None

    def _infer_specialty(self, q: str) -> str:
        q = q.lower()
        for spec, kws in {"property":["property","land","rent","eviction"],"family":["divorce","custody","marriage"],
                "criminal":["criminal","bail","fir","ipc"],"corporate":["company","director","merger"],
                "tax":["tax","gst","income tax"],"ip":["patent","trademark","copyright"],
                "consumer":["consumer","defective"],"cyber":["cyber","data breach","fraud"],
                "labour":["labour","employment","termination"],"banking":["banking","loan","sarfaesi"]}.items():
            if any(k in q for k in kws): return spec
        return "general"

    async def auto_create_agent(self, proposal: Dict) -> Dict:
        slug = proposal.get("proposed_agent_slug","auto-agent"); spec = proposal.get("proposed_specialty","general")
        persona = {"name":f"Auto-Specialist: {spec.title()}","specialization":spec,
                   "system_prompt":f"You are a specialized legal AI agent for {spec} law.","auto_created":True}
        registered = False
        try:
            from ..core import agent_registry
            if hasattr(agent_registry,"register"): agent_registry.register(slug=slug,name=persona["name"],persona=persona); registered=True
            elif hasattr(agent_registry,"add"): agent_registry.add(slug=slug,name=persona["name"],persona=persona); registered=True
        except Exception as e: log.warning(f"Could not register agent in v40.0: {e}")
        await db.add_agent_version(slug, persona, 0.3, "auto-created for knowledge gap")
        await db.audit("evolution","agent_auto_created","agent",slug,{"specialty":spec,"registered":registered})
        return {"agent_slug":slug,"specialty":spec,"registered":registered}

    async def stats(self) -> Dict:
        s = await db.stats()
        return {"total_learnings":s.get("moat_learnings",0),"agent_versions":s.get("moat_agent_versions",0),"mesh_enabled":True}

evolution = EvolutionEngine()
