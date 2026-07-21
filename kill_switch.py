# =============================================================================
# kill_switch.py – Emergency Safety Mechanisms
# =============================================================================

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any  # ✅ Added required imports

logger = logging.getLogger("unknown_verdict.killswitch")

class KillSwitch:
    """Emergency shutdown mechanism with multiple activation triggers."""
    
    def __init__(self, pg_pool, redis_pool=None):
        self.pg_pool = pg_pool
        self.redis_pool = redis_pool
        self.is_active = True
        self.shutdown_reason = None
        self.shutdown_time = None
        self.triggers = self._load_triggers()
    
    def _load_triggers(self) -> Dict:  # ✅ Now Dict is defined
        return {
            "constitutional_violation": {"threshold": 5, "window_minutes": 60},
            "red_team_escape": {"threshold": 1, "window_minutes": 0},
            "anomaly_detection": {"threshold": 3, "window_minutes": 10}
        }
    
    async def check_triggers(self) -> bool:
        for trigger_name, config in self.triggers.items():
            count = await self._get_trigger_count(trigger_name, config["window_minutes"])
            if count >= config["threshold"]:
                await self.activate(f"Trigger '{trigger_name}' exceeded threshold: {count}")
                return True
        return False
    
    async def _get_trigger_count(self, trigger_name: str, window_minutes: int) -> int:
        try:
            async with self.pg_pool.acquire() as conn:
                if window_minutes == 0:
                    query = "SELECT COUNT(*) FROM trigger_events WHERE trigger_name = $1 AND created_at > NOW()"
                else:
                    query = f"SELECT COUNT(*) FROM trigger_events WHERE trigger_name = $1 AND created_at > NOW() - INTERVAL '{window_minutes} minutes'"
                return await conn.fetchval(query, trigger_name) or 0
        except Exception as e:
            logger.error(f"Failed to get trigger count: {e}")
            return 0
    
    async def activate(self, reason: str):
        self.is_active = False
        self.shutdown_reason = reason
        self.shutdown_time = datetime.now()
        logger.critical(f"⚠️ KILL SWITCH ACTIVATED: {reason}")
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO kill_switch_logs (reason, activated_at, status) 
                    VALUES ($1, $2, 'ACTIVE')
                """, reason, self.shutdown_time)
        except Exception as e:
            logger.error(f"Failed to log kill switch activation: {e}")
    
    async def deactivate(self, reason: str, authorized_by: str) -> bool:
        self.is_active = True
        self.shutdown_reason = None
        self.shutdown_time = None
        logger.info(f"✅ Kill switch deactivated by {authorized_by}: {reason}")
        return True
    
    async def log_event(self, event_type: str, details: Dict):
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO trigger_events (trigger_name, details, created_at) 
                    VALUES ($1, $2, NOW())
                """, event_type, json.dumps(details))
        except Exception as e:
            logger.error(f"Failed to log trigger event: {e}")