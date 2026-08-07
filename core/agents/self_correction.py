"""
core/agents/self_correction.py - Self-Correction Loop
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)

# Try to import db, but don't fail if not available
try:
    from core.db import db
except ImportError:
    db = None
    logger.warning("⚠️ Database not available - self_correction in fallback mode")


class SelfCorrectionLoop:
    """Self-correction loop for continuous improvement"""
    
    def __init__(self):
        self.router = get_router()
        self.correction_history = []
        self.error_patterns = defaultdict(int)
    
    async def analyze_error(self, error: Dict) -> Dict:
        """Analyze error and suggest corrections"""
        messages = [
            LLMMessage(role="system", content="""You are a self-correction expert.
            Analyze the error and suggest specific corrections.
            Return JSON with: root_cause, suggested_fixes, priority, impact"""),
            LLMMessage(role="user", content=f"Error:\n{json.dumps(error, indent=2)}")
        ]
        
        try:
            response = await self.router.chat(messages, complexity="complex")
            analysis = json.loads(response.content)
        except:
            analysis = {
                'root_cause': 'Unknown',
                'suggested_fixes': ['Manual review required'],
                'priority': 'medium',
                'impact': 'low'
            }
        
        # Track error pattern
        error_type = error.get('type', 'unknown')
        self.error_patterns[error_type] += 1
        
        correction = {
            'error': error,
            'analysis': analysis,
            'suggested_fixes': analysis.get('suggested_fixes', []),
            'priority': analysis.get('priority', 'medium'),
            'timestamp': datetime.now().isoformat()
        }
        
        self.correction_history.append(correction)
        
        # Store in database if available
        if db:
            try:
                await self._store_correction(correction)
            except Exception as e:
                logger.error(f"Error storing correction: {e}")
        
        return correction
    
    async def _store_correction(self, correction: Dict):
        """Store correction in database"""
        if not db:
            return
        
        try:
            await db.execute("""
                INSERT INTO self_corrections 
                (error_type, analysis, fixes, priority, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """,
                correction['error'].get('type', 'unknown'),
                json.dumps(correction['analysis']),
                json.dumps(correction['suggested_fixes']),
                correction['priority'],
                correction['timestamp']
            )
        except Exception as e:
            logger.error(f"Error storing correction: {e}")
    
    async def get_correction_history(self, limit: int = 50) -> List[Dict]:
        """Get correction history"""
        if db:
            try:
                rows = await db.fetchall("""
                    SELECT * FROM self_corrections 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """, limit)
                return [dict(row) for row in rows]
            except:
                pass
        
        return self.correction_history[-limit:]
    
    async def get_insights(self) -> Dict:
        """Get self-correction insights"""
        total = sum(self.error_patterns.values())
        
        return {
            'total_errors': total,
            'error_patterns': dict(self.error_patterns),
            'most_common': max(self.error_patterns.items(), key=lambda x: x[1])[0] if self.error_patterns else None,
            'history_count': len(self.correction_history),
            'timestamp': datetime.now().isoformat()
        }


# Singleton instance
self_correction = SelfCorrectionLoop()