"""Feature 14: Outcome-Based Pricing Engine."""
from __future__ import annotations
from typing import Any, Dict
from .db import db
from .predictive import predictive
from .sarvam import sarvam_reason

class PricingEngine:
    async def price_case(self, case_summary: str, case_type: str = "civil") -> Dict[str, Any]:
        prediction = await predictive.predict_outcome(case_summary, case_type)
        confidence = prediction["confidence"]
        # Base fee: ₹3,500/hour * estimated 20 hours
        base_fee = 3500 * 20
        # Success fee: 12% of estimated case value if confidence > 0.65
        success_pct = 12.0 if confidence > 0.65 else 8.0
        estimated_value = 500000  # default
        success_fee = int(estimated_value * success_pct / 100)
        total = base_fee + (success_fee if confidence > 0.6 else 0)
        pid = await db.add_pricing(case_summary, prediction["predicted_outcome"],
                                   confidence, base_fee, success_pct, estimated_value)
        return {"pricing_id":pid or "","pricing_model":"outcome_based",
                "base_fee_inr":base_fee,"success_fee_pct":success_pct,
                "estimated_success_fee_inr":success_fee if confidence > 0.6 else 0,
                "total_estimated_inr":total,
                "outcome_prediction":prediction["predicted_outcome"],
                "confidence":confidence,
                "roi_projection":f"{round((estimated_value-total)/total*100,1)}% if won"}

    async def value_report(self, case_summary: str) -> Dict[str, Any]:
        p = await self.price_case(case_summary)
        return {"report":"Outcome-based pricing aligns our fee with your success.",
                "pricing":p,"recommendation":"Proceed with outcome-based pricing for risk alignment"}

pricing = PricingEngine()
