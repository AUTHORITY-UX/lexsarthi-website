"""
Moat Integration – Connects Moat Intelligence with Shakti Judge.
"""

import logging
from typing import Dict, Any
from core.judge.shakti import get_shakti
from core.moat.evolution import get_evolution
from core.moat.predictive import get_predictive

logger = logging.getLogger(__name__)


class MoatIntegration:
    """Integrates Moat Intelligence with Shakti Judge."""

    def __init__(self):
        self.shakti = get_shakti()
        self.evolution = get_evolution()
        self.predictive = get_predictive()

    async def process_with_moat(self, query: str) -> Dict[str, Any]:
        """Process a query through Moat + Shakti."""
        # 1. Get predictive insight
        prediction = await self.predictive.predict_outcome(query)

        # 2. Get verdict from Shakti
        verdict = await self.shakti.deliver_verdict(query)

        # 3. Record learning
        await self.evolution.record_learning({
            "query": query,
            "verdict": verdict,
            "prediction": prediction
        })

        return {
            "query": query,
            "verdict": verdict,
            "prediction": prediction,
            "learning_recorded": True,
            "timestamp": "2026-08-29T19:27:38.272070"
        }


_moat_integration = None

def get_moat_integration():
    global _moat_integration
    if _moat_integration is None:
        _moat_integration = MoatIntegration()
    return _moat_integration