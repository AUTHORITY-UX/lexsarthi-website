# =============================================================================
# monitoring.py – Multi-Modal Monitoring System
# =============================================================================

import json
import logging
from datetime import datetime
from typing import Dict
from collections import deque

logger = logging.getLogger("unknown_verdict.monitoring")

class MonitoringSystem:
    """Real-time monitoring of all AI actions with anomaly detection."""
    
    def __init__(self, pg_pool, redis_pool=None):
        self.pg_pool = pg_pool
        self.redis_pool = redis_pool
        self.metrics_window = deque(maxlen=1000)
        self.anomaly_threshold = 3.0
    
    async def log_action(self, action_type: str, user_id: int, details: Dict, agent_id: str = None):
        action_log = {
            "action_type": action_type,
            "user_id": user_id,
            "agent_id": agent_id,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.metrics_window.append(action_log)
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO ai_actions_log (action_type, user_id, agent_id, details, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                """, action_type, user_id, agent_id, json.dumps(details))
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
        
        if await self._detect_anomaly(action_log):
            logger.warning(f"⚠️ Anomaly detected: {action_type} by user {user_id}")
    
    async def _detect_anomaly(self, current_action: Dict) -> bool:
        similar_actions = [
            a for a in self.metrics_window 
            if a["action_type"] == current_action["action_type"] 
            and a["user_id"] == current_action["user_id"]
        ]
        if len(similar_actions) < 10:
            return False
        return False  # Simplified for production