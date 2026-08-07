"""
core/governance/regulatory_tracker.py - Global Regulatory Intelligence
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import httpx

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


class GlobalRegulatoryTracker:
    """Track global AI regulations and updates"""
    
    REGULATIONS = {
        'eu_ai_act': {
            'name': 'EU AI Act',
            'jurisdiction': 'European Union',
            'status': 'active',
            'effective_date': '2024-08-01',
            'risk_levels': ['unacceptable', 'high', 'limited', 'minimal'],
            'url': 'https://artificialintelligenceact.eu'
        },
        'dpdpa': {
            'name': 'DPDPA',
            'jurisdiction': 'India',
            'status': 'active',
            'effective_date': '2023-08-11',
            'risk_levels': ['high', 'medium', 'low'],
            'url': 'https://meity.gov.in'
        },
        'gdpr': {
            'name': 'GDPR',
            'jurisdiction': 'European Union',
            'status': 'active',
            'effective_date': '2018-05-25',
            'url': 'https://gdpr.eu'
        },
        'data_act': {
            'name': 'EU Data Act',
            'jurisdiction': 'European Union',
            'status': 'active',
            'effective_date': '2023-01-01',
            'url': 'https://digital-strategy.ec.europa.eu'
        },
        'hipaa': {
            'name': 'HIPAA',
            'jurisdiction': 'USA',
            'status': 'active',
            'effective_date': '1996-08-21',
            'url': 'https://hhs.gov/hipaa'
        },
        'ccpa': {
            'name': 'CCPA',
            'jurisdiction': 'USA (California)',
            'status': 'active',
            'effective_date': '2020-01-01',
            'url': 'https://oag.ca.gov/privacy/ccpa'
        },
        'uk_ai': {
            'name': 'UK AI Regulation',
            'jurisdiction': 'United Kingdom',
            'status': 'active',
            'effective_date': '2024-01-01',
            'url': 'https://gov.uk/ai'
        },
        'japan_ai': {
            'name': 'Japan AI Act',
            'jurisdiction': 'Japan',
            'status': 'pending',
            'effective_date': '2025-04-01',
            'url': 'https://meti.go.jp'
        },
        'brazil_ai': {
            'name': 'Brazil AI Regulation',
            'jurisdiction': 'Brazil',
            'status': 'pending',
            'effective_date': '2025-01-01',
            'url': 'https://gov.br'
        },
        'australia_ai': {
            'name': 'Australia AI Framework',
            'jurisdiction': 'Australia',
            'status': 'pending',
            'effective_date': '2025-06-01',
            'url': 'https://industry.gov.au'
        },
        'singapore_ai': {
            'name': 'Singapore AI Governance',
            'jurisdiction': 'Singapore',
            'status': 'active',
            'effective_date': '2024-12-01',
            'url': 'https://imda.gov.sg'
        },
        'canada_ai': {
            'name': 'Canada AI Data Act',
            'jurisdiction': 'Canada',
            'status': 'active',
            'effective_date': '2024-06-01',
            'url': 'https://ised-isde.canada.ca'
        }
    }
    
    def __init__(self):
        self.router = get_router()
        self.client = httpx.AsyncClient(timeout=30.0)
        self.updates = []
    
    async def get_all_regulations(self) -> Dict:
        """Get all regulations with status"""
        return self.REGULATIONS
    
    async def get_compliance_status(self, tenant_id: str) -> Dict:
        """Get compliance status for tenant"""
        compliance = {}
        for reg_id, reg in self.REGULATIONS.items():
            status = await self._check_compliance(tenant_id, reg_id)
            compliance[reg_id] = {
                'name': reg['name'],
                'jurisdiction': reg['jurisdiction'],
                'status': status,
                'effective_date': reg.get('effective_date', 'unknown'),
                'risk_levels': reg.get('risk_levels', [])
            }
        return compliance
    
    async def _check_compliance(self, tenant_id: str, reg_id: str) -> str:
        """Check compliance for specific regulation"""
        try:
            row = await db.fetchone("""
                SELECT status FROM compliance_status 
                WHERE tenant_id = $1 AND regulation_id = $2
                ORDER BY checked_at DESC LIMIT 1
            """, tenant_id, reg_id)
            return row['status'] if row else 'unknown'
        except:
            return 'unknown'
    
    async def track_global_changes(self) -> Dict:
        """Track global regulatory changes"""
        changes = []
        
        for reg_id, reg in self.REGULATIONS.items():
            if reg.get('status') == 'pending':
                changes.append({
                    'regulation': reg['name'],
                    'jurisdiction': reg['jurisdiction'],
                    'change': 'New regulation pending',
                    'effective_date': reg.get('effective_date', 'unknown'),
                    'impact': 'high'
                })
            elif reg.get('status') == 'updated':
                changes.append({
                    'regulation': reg['name'],
                    'jurisdiction': reg['jurisdiction'],
                    'change': 'Regulation updated',
                    'effective_date': reg.get('effective_date', 'unknown'),
                    'impact': 'medium'
                })
        
        # Add recent news
        news = await self._fetch_regulatory_news()
        changes.extend(news)
        
        return {
            'changes': changes,
            'count': len(changes),
            'last_updated': datetime.now().isoformat()
        }
    
    async def _fetch_regulatory_news(self) -> List[Dict]:
        """Fetch regulatory news from RSS feeds"""
        news = []
        
        try:
            import feedparser
            feeds = [
                'https://artificialintelligenceact.eu/feed/',
                'https://gdpr.eu/feed/',
                'https://digital-strategy.ec.europa.eu/rss'
            ]
            
            for feed_url in feeds:
                try:
                    response = await self.client.get(feed_url)
                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        for entry in feed.entries[:3]:
                            news.append({
                                'regulation': 'EU AI Act',
                                'jurisdiction': 'European Union',
                                'change': entry.get('title', ''),
                                'effective_date': datetime.now().isoformat(),
                                'impact': 'medium'
                            })
                except:
                    pass
        except:
            pass
        
        return news[:10]
    
    async def get_global_dashboard(self) -> Dict:
        """Get global regulatory dashboard"""
        total = len(self.REGULATIONS)
        active = len([r for r in self.REGULATIONS.values() if r.get('status') == 'active'])
        pending = len([r for r in self.REGULATIONS.values() if r.get('status') == 'pending'])
        
        return {
            'total_regulations': total,
            'active_regulations': active,
            'pending_regulations': pending,
            'compliance_rate': (active / total * 100) if total > 0 else 0,
            'regulations': self.REGULATIONS,
            'last_updated': datetime.now().isoformat()
        }
    
    async def start_background_tracker(self, interval_minutes: int = 60):
        """Start background regulatory tracking"""
        while True:
            try:
                logger.info("🔄 Tracking global regulatory changes...")
                changes = await self.track_global_changes()
                self.updates = changes.get('changes', [])
                logger.info(f"✅ Found {len(self.updates)} regulatory changes")
            except Exception as e:
                logger.error(f"Error tracking regulations: {e}")
            await asyncio.sleep(interval_minutes * 60)


regulatory_tracker = GlobalRegulatoryTracker()