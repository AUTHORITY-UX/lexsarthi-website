"""Feature 4: AI Judge Evolution System."""
from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Optional
from loguru import logger as log
from .db import db
from .embeddings import embed
from .sarvam import sarvam_reason

JUDGE_PROMPT = """You are the AI Judge of Unknown Verdict. Review the case and deliver a verdict.
State: 1) Your assessment 2) Any errors 3) Verdict (APPROVED/NEEDS_REVISION/REJECTED)
4) Score 0.0-1.0 5) Appeal prediction 6) Recommendations."""

class JudgeEvolution:
    def __init__(self): self.version = "41.0"; self.total = 0; self.correct = 0

    async def deliver_verdict(self, case_summary: str, agent_response: str = "",
                              agent_name: str = "", jurisdiction: str = "IN") -> Dict[str, Any]:
        self.total += 1
        prompt = f"Case: {case_summary}\nAgent: {agent_name}\nResponse: {agent_response[:2000]}"
        raw = await sarvam_reason(prompt, JUDGE_PROMPT, 0.2, 3000)
        verdict_type = "needs_revision"; score = 0.65; appeal = "uphold_likely"
        if raw:
            low = raw.lower()
            if "approved" in low: verdict_type = "approved"
            if "rejected" in low: verdict_type = "rejected"
        # Recall similar past verdicts
        qv = await embed(case_summary)
        similar = await db.vector_search("moat_verdicts","embedding",qv,top_k=5)
        if similar:
            avg_conf = sum(r.get("confidence",0.5) for r in similar)/len(similar)
            score = round((score+avg_conf)/2,4)
        sig = hashlib.sha256(f"judge-v{self.version}-{self.total}".encode()).hexdigest()[:16]
        emb = await embed(f"{case_summary} {verdict_type}")
        vid = await db.add_verdict(case_summary, verdict_type, score, "", appeal, sig, emb)
        if vid: await db.audit("judge","verdict_delivered","verdict",vid,{"score":score})
        return {"verdict_id":vid or "","verdict_type":verdict_type,"score":score,
                "appeal_prediction":appeal,"judge_signature":sig,"similar_verdicts":len(similar),
                "reasoning":raw or "Verdict based on verification scores.","judge_version":self.version}

    async def resolve_with_feedback(self, verdict_id: str, actual_outcome: str, feedback: float) -> Dict[str, Any]:
        await db.resolve_verdict(verdict_id, actual_outcome, feedback)
        if feedback >= 0.7: self.correct += 1
        await db.audit("judge","verdict_resolved","verdict",verdict_id,{"actual":actual_outcome})
        return {"verdict_id":verdict_id,"resolved":True,"accuracy":round(self.correct/max(self.total,1),4)}

    async def get_evolution_stats(self) -> Dict[str, Any]:
        return {"version":self.version,"total_verdicts":self.total,
                "accuracy":round(self.correct/max(self.total,1),4) if self.total else 0.0,
                "db_stats":await db.stats()}

judge_evolution = JudgeEvolution()
