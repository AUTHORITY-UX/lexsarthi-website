"""Feature 2: Proprietary IRAC Legal Reasoning Engine."""
from __future__ import annotations
import re, json
from typing import Any, Dict, List, Optional
from loguru import logger as log
from .db import db
from .embeddings import embed
from .sarvam import sarvam_reason

IRAC_PROMPT = """You are a legal reasoning engine using the IRAC method.
For the given scenario, produce structured analysis:
ISSUE: Identify the precise legal issue(s).
RULE: State the applicable rules, statutes, and precedent.
APPLICATION: Apply rules to facts, weighing precedent strength.
CONCLUSION: State the likely outcome with confidence level.
Cross-reference across jurisdictions where relevant. Cite specific sections and case law."""

class IRACEngine:
    async def reason(self, case_summary: str, jurisdiction: str = "IN",
                      agent_id: str = "", precedents: Optional[List[str]] = None) -> Dict[str, Any]:
        qv = await embed(case_summary)
        similar = await db.vector_search("moat_reasoning_patterns","embedding",qv,top_k=5,
                                          where="jurisdiction = $2", params=(jurisdiction,))
        ctx = ""
        if similar:
            ctx = "\n\nSimilar past reasoning:"
            for s in similar[:3]:
                ctx += f"\n- Issue: {s.get('issue','')[:200]} -> {s.get('conclusion','')[:200]}"
        prompt = f"Jurisdiction: {jurisdiction}\nCase: {case_summary}{ctx}"
        if precedents: prompt += f"\nRelevant precedents: {'; '.join(precedents[:5])}"
        raw = await sarvam_reason(prompt, IRAC_PROMPT, 0.3, 4096)
        parsed = self._parse_irac(raw)
        weights = {s.get("id",""):round(s.get("similarity",0)*s.get("confidence",0.5),4) for s in similar if s.get("id")}
        conf = parsed.get("confidence",0.65)
        if similar:
            avg_sim = sum(s.get("similarity",0) for s in similar)/len(similar)
            conf = round((conf+avg_sim)/2,4)
        emb = await embed(f"{parsed['issue']} {parsed['conclusion']}")
        rid = await db.add_reasoning(parsed["issue"],parsed["rule"],parsed["application"],
                                      parsed["conclusion"],weights,jurisdiction,parsed.get("outcome","pending"),
                                      conf,agent_id,True,emb)
        return {"reasoning_id":rid or "","issue":parsed["issue"],"rule":parsed["rule"],
                "application":parsed["application"],"conclusion":parsed["conclusion"],
                "confidence":conf,"precedent_weights":weights,"similar_patterns":len(similar),
                "sarvam_used":bool(raw)}

    def _parse_irac(self, text: str) -> Dict:
        if not text:
            return {"issue":"","rule":"","application":"","conclusion":"","confidence":0.5,"outcome":"pending"}
        return {"issue":self._extract(text,"ISSUE"),"rule":self._extract(text,"RULE"),
                "application":self._extract(text,"APPLICATION"),"conclusion":self._extract(text,"CONCLUSION"),
                "confidence":0.65,"outcome":"pending"}

    def _extract(self, text: str, sec: str) -> str:
        pat = rf"{sec}:?\s*(.*?)(?=(?:ISSUE|RULE|APPLICATION|CONCLUSION|CONFIDENCE):?|$)"
        m = re.search(pat, text, re.IGNORECASE|re.DOTALL)
        return m.group(1).strip() if m else ""

    async def cross_jurisdiction(self, case_summary: str, jurisdictions: List[str]) -> Dict[str, Any]:
        results = {}
        for j in jurisdictions: results[j] = await self.reason(case_summary, j)
        avg = sum(r.get("confidence",0.5) for r in results.values())/len(results) if results else 0.5
        consensus = "strong" if avg>0.75 else "moderate" if avg>0.6 else "divergent"
        return {"jurisdictional_analysis":results,"jurisdictions":jurisdictions,"consensus":consensus}

    async def search_patterns(self, query: str, top_k: int = 10) -> List[Dict]:
        qv = await embed(query)
        rows = await db.vector_search("moat_reasoning_patterns","embedding",qv,top_k)
        return [{"id":r.get("id"),"issue":r.get("issue"),"conclusion":r.get("conclusion"),
                 "confidence":r.get("confidence"),"similarity":round(r.get("similarity",0),4)} for r in rows]

irac_engine = IRACEngine()
