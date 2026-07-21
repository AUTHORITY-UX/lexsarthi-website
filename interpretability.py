# =============================================================================
# interpretability.py – AI Decision Transparency
# =============================================================================

import json
import logging
from typing import Dict

logger = logging.getLogger("unknown_verdict.interpretability")

class InterpretabilityDashboard:
    """Provides real-time visibility into AI decision-making."""
    
    def __init__(self, pg_pool):
        self.pg_pool = pg_pool
    
    async def log_decision_path(self, query_id: int, decision_path: Dict):
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO decision_paths (query_id, decision_path, created_at)
                    VALUES ($1, $2, NOW())
                """, query_id, json.dumps(decision_path))
        except Exception as e:
            logger.error(f"Failed to log decision path: {e}")
    
    async def explain_response(self, query_id: int) -> Dict:
        try:
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT q.query, q.response, d.final_answer, d.confidence, 
                           d.domain, d.persona, d.verifier_results
                    FROM queries q
                    JOIN deliberations d ON q.id = d.query_id
                    WHERE q.id = $1
                """, query_id)
                if not row:
                    return {"error": "Query not found"}
                return {
                    "query": row['query'],
                    "response": row['response'],
                    "confidence": row['confidence'],
                    "agent_used": row['persona'],
                    "jury_deliberations": json.loads(row['verifier_results']) if row['verifier_results'] else {}
                }
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return {"error": str(e)}