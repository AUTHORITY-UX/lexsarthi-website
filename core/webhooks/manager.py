"""
core/webhooks/manager.py - Webhook Integration
"""

import json
import logging
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.db import db

logger = logging.getLogger(__name__)


class WebhookManager:
    """Webhook management and delivery"""
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.retry_delays = [60, 300, 900]  # 1min, 5min, 15min
    
    async def register_webhook(self, tenant_id: str, url: str, 
                               events: List[str], secret: str = None) -> Dict:
        """Register a webhook for tenant"""
        try:
            row = await db.fetchrow("""
                INSERT INTO webhooks (tenant_id, url, events, secret, created_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, tenant_id, url, events, secret, datetime.now())
            
            return {
                'id': str(row['id']) if row else None,
                'tenant_id': tenant_id,
                'url': url,
                'events': events,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error registering webhook: {e}")
            return {'error': str(e)}
    
    async def get_webhooks(self, tenant_id: str) -> List[Dict]:
        """Get all webhooks for tenant"""
        try:
            rows = await db.fetchall(
                "SELECT * FROM webhooks WHERE tenant_id = $1 AND is_active = TRUE",
                tenant_id
            )
            return [dict(row) for row in rows]
        except:
            return []
    
    async def trigger_webhook(self, tenant_id: str, event: str, data: Dict):
        """Trigger webhook for event"""
        webhooks = await self.get_webhooks(tenant_id)
        
        for webhook in webhooks:
            if event not in webhook.get('events', []):
                continue
            
            await self._deliver_webhook(webhook, event, data)
    
    async def _deliver_webhook(self, webhook: Dict, event: str, data: Dict):
        """Deliver webhook with retry logic"""
        payload = {
            'event': event,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        for attempt, delay in enumerate(self.retry_delays + [0]):
            try:
                response = await self.client.post(
                    webhook['url'],
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Webhook-Event': event,
                        'X-Webhook-Delivery': str(datetime.now().timestamp())
                    }
                )
                
                await self._log_delivery(
                    webhook['id'],
                    event,
                    response.status_code,
                    attempt + 1
                )
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook delivered: {webhook['url']}")
                    return
                
                if attempt < len(self.retry_delays):
                    logger.warning(f"Webhook failed, retrying in {delay}s: {webhook['url']}")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Webhook delivery error: {e}")
                await self._log_delivery(
                    webhook['id'],
                    event,
                    500,
                    attempt + 1,
                    str(e)
                )
    
    async def _log_delivery(self, webhook_id: str, event: str, 
                           status: int, attempt: int = 1, error: str = None):
        """Log webhook delivery"""
        try:
            await db.execute("""
                INSERT INTO webhook_deliveries 
                (webhook_id, event, status, attempt, error, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, webhook_id, event, status, attempt, error, datetime.now())
        except Exception as e:
            logger.error(f"Error logging webhook delivery: {e}")


webhook_manager = WebhookManager()