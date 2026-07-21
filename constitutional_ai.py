# =============================================================================
# constitutional_ai.py – Constitutional AI Layer
# =============================================================================

import json
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger("unknown_verdict.constitutional")

class ConstitutionalAI:
    """
    Implements Constitutional AI (inspired by Anthropic's approach)
    with Indian Constitutional values embedded in the training loop.
    """
    
    def __init__(self, pg_pool):
        self.pg_pool = pg_pool
        self.constitution = self._load_constitution()
        self.ethics_principles = self._load_ethics_principles()
        
    def _load_constitution(self) -> Dict:
        """Load Indian Constitutional values as safety constraints"""
        return {
            "preamble": {
                "justice": "Social, economic, and political justice",
                "liberty": "Freedom of thought, expression, belief, faith, and worship",
                "equality": "Equality of status and of opportunity",
                "fraternity": "Assuring dignity of the individual"
            },
            "fundamental_rights": {
                "article_14": "Equality before law",
                "article_15": "Prohibition of discrimination",
                "article_19": "Freedom of speech and expression",
                "article_21": "Protection of life and personal liberty",
                "article_22": "Protection against arbitrary arrest"
            }
        }
    
    def _load_ethics_principles(self) -> Dict:
        return {
            "beneficence": "AI should benefit humanity and avoid harm",
            "non_maleficence": "AI should not cause unnecessary harm",
            "autonomy": "AI should respect human autonomy",
            "justice": "AI should be fair and distribute benefits/risks equitably",
            "transparency": "AI should be explainable and accountable",
            "privacy": "AI should protect personal data"
        }
    
    async def evaluate_response(self, query: str, response: str, context: Dict) -> Dict:
        violations = []
        corrected_response = response
        score = 1.0
        
        if self._violates_fundamental_rights(response):
            violations.append("Fundamental Rights violation detected")
            score *= 0.6
        
        if self._violates_ethics(response):
            violations.append("Ethics violation detected")
            score *= 0.7
        
        if self._has_discriminatory_content(response):
            violations.append("Discriminatory content detected")
            score *= 0.3
            corrected_response = await self._safe_response_generation(query)
        
        if score >= 0.8:
            compliance = "HIGH"
        elif score >= 0.5:
            compliance = "MEDIUM"
        else:
            compliance = "LOW"
        
        if violations:
            await self._log_violation(query, response, violations, score)
        
        return {
            "constitutional_check": len(violations) == 0,
            "ethics_compliance": compliance,
            "violations": violations,
            "corrected_response": corrected_response,
            "confidence": score
        }
    
    def _violates_fundamental_rights(self, text: str) -> bool:
        indicators = ["discriminate", "caste", "religion", "gender", "untouchability", "arbitrary arrest"]
        return any(v in text.lower() for v in indicators)
    
    def _violates_ethics(self, text: str) -> bool:
        indicators = ["harm", "exploit", "unfair", "bias", "deceive", "violate privacy"]
        return any(v in text.lower() for v in indicators)
    
    def _has_discriminatory_content(self, text: str) -> bool:
        patterns = [r'\b(caste|religion|gender|race)\b.*\b(inferior|superior)\b']
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    async def _safe_response_generation(self, query: str) -> str:
        from app import call_llm
        system = "You are a safe AI assistant. Generate a constructive, ethical response."
        prompt = f"Original query: {query}\n\nGenerate a safe, ethical response:"
        return await call_llm(system, prompt, provider="groq") or "I cannot provide a response to this query as it may involve harmful content."
    
    async def _log_violation(self, query: str, response: str, violations: List[str], score: float):
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO constitutional_violations 
                    (query, response, violations, confidence_score, detected_at)
                    VALUES ($1, $2, $3, $4, NOW())
                """, query, response, json.dumps(violations), score)
        except Exception as e:
            logger.error(f"Failed to log constitutional violation: {e}")