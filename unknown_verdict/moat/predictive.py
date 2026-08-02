"""Feature 5: Predictive Analytics Engine."""
from __future__ import annotations
from typing import Any, Dict, List
from .db import db
from .embeddings import embed
from .sarvam import sarvam_reason

class PredictiveAnalytics:
    async def predict_outcome(self, case_summary: str, case_type: str = "",
                              jurisdiction: str = "IN") -> Dict[str, Any]:
        qv = await embed(case_summary)
        similar = await db.vector_search("moat_verdicts","embedding",qv,top_k=10)
        # Calculate probability distribution from similar cases
        outcomes = {}
        for s in similar:
            ot = s.get("decision","unknown")
            outcomes[ot] = outcomes.get(ot, 0) + 1
        total_sim = sum(outcomes.values()) or 1
        dist = {k: round(v/total_sim, 4) for k, v in outcomes.items()}
        # Get LLM analysis
        raw = await sarvam_reason(f"Predict outcome for: {case_summary[:2000]}",
                                  "You are a legal outcome predictor. State predicted outcome and confidence (0-1).",0.3,1500)
        confidence = 0.65
        if similar:
            avg_sim = sum(s.get("similarity",0) for s in similar)/len(similar)
            confidence = round(0.5 + avg_sim * 0.4, 4)
        predicted = max(dist, key=dist.get) if dist else "plaintiff_prevails"
        pid = await db.add_prediction(case_summary, "outcome", predicted, confidence, raw or "", qv)
        return {"prediction_id":pid or "","predicted_outcome":predicted,
                "confidence":confidence,"probability_distribution":dist,
                "similar_cases":len(similar),"rationale":raw or "Based on similar case analysis"}

    async def predict_settlement(self, case_summary: str) -> Dict[str, Any]:
        raw = await sarvam_reason(f"Assess settlement likelihood: {case_summary[:2000]}",
                                  "State settlement probability (0-1) and expected range.",0.3,1000)
        return {"prediction_type":"settlement","analysis":raw or "Settlement analysis requires more data",
                "confidence":0.6}

    async def predict_timeline(self, case_summary: str, case_type: str = "civil") -> Dict[str, Any]:
        timelines = {"civil":"18-36 months","criminal":"12-48 months","commercial":"12-24 months",
                     "family":"6-18 months","consumer":"6-12 months"}
        raw = await sarvam_reason(f"Estimate timeline for: {case_summary[:1500]}",
                                  "Provide estimated timeline in months.",0.3,800)
        return {"prediction_type":"timeline","estimated_range":timelines.get(case_type,"12-24 months"),
                "analysis":raw or "Timeline estimate based on case type"}

    async def predict_cost(self, case_summary: str, case_type: str = "civil") -> Dict[str, Any]:
        raw = await sarvam_reason(f"Estimate legal costs for: {case_summary[:1500]}",
                                  "Provide cost estimate in INR (court fees + lawyer fees).",0.3,800)
        return {"prediction_type":"cost","estimated_range":"₹50,000 - ₹5,00,000",
                "analysis":raw or "Cost estimate based on case complexity"}

    async def predict_judge_behavior(self, judge_id: str = "") -> Dict[str, Any]:
        return {"prediction_type":"judge_behavior","judge_id":judge_id or "general",
                "tendency":"analysis requires judge-specific historical data",
                "note":"Collect more verdict data for accurate judge profiling"}

predictive = PredictiveAnalytics()
