"""
core/agents/self_correction.py - Self-Correction Loop
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


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
        
        response = await self.router.chat(messages, complexity="complex")
        
        try:
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
        await self._store_correction(correction)
        
        return correction
    
    async def _store_correction(self, correction: Dict):
        """Store correction in database"""
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
        try:
            rows = await db.fetchall("""
                SELECT * FROM self_corrections 
                ORDER BY created_at DESC 
                LIMIT $1
            """, limit)
            return [dict(row) for row in rows]
        except:
            return self.correction_history[-limit:]
    
    async def apply_correction(self, correction_id: str) -> Dict:
        """Apply a correction"""
        try:
            row = await db.fetchone(
                "SELECT * FROM self_corrections WHERE id = $1",
                correction_id
            )
            if not row:
                return {'error': 'Correction not found'}
            
            await db.execute(
                "UPDATE self_corrections SET applied = TRUE WHERE id = $1",
                correction_id
            )
            
            return {
                'status': 'applied',
                'correction': dict(row)
            }
        except Exception as e:
            return {'error': str(e)}
    
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


self_correction = SelfCorrectionLoop()