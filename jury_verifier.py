# jury_verifier.py - 20 verifiers scoring responses
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncio
import logging
from typing import List, Dict

from llm_client import call_llm

logger = logging.getLogger(__name__)

class JuryVerifier:
    def __init__(self):
        self.verifiers = self._load_verifiers()

    def _load_verifiers(self) -> List[Dict]:
        # 20 verifiers with specific roles
        return [
            {"id": "v01", "name": "Ganesha", "role": "Citation & logic integrity", "prompt": "Check citations and logical flow."},
            {"id": "v02", "name": "Saraswati", "role": "Knowledge cross‑reference", "prompt": "Verify facts against established knowledge."},
            {"id": "v03", "name": "Hanuman", "role": "Global compliance", "prompt": "Ensure compliance with international norms."},
            {"id": "v04", "name": "Kartikeya", "role": "Contradiction detection", "prompt": "Find internal contradictions."},
            {"id": "v05", "name": "Indra", "role": "Jurisdiction mapping", "prompt": "Confirm jurisdiction is correct."},
            {"id": "v06", "name": "Yama", "role": "Bias & neutrality", "prompt": "Detect any bias in reasoning."},
            {"id": "v07", "name": "Surya", "role": "Timeline & limitation", "prompt": "Check if statutes are current."},
            {"id": "v08", "name": "Chandra", "role": "Precedent match", "prompt": "Match with known precedents."},
            {"id": "v09", "name": "Vayu", "role": "PII / privacy filter", "prompt": "Redact any PII."},
            {"id": "v10", "name": "Shakti", "role": "Final judge & dharma seal", "prompt": "Synthesise critiques."},
            {"id": "v11", "name": "Brahma", "role": "Factual accuracy", "prompt": "Verify factual claims."},
            {"id": "v12", "name": "Vishnu", "role": "Ethical review", "prompt": "Check ethical implications."},
            {"id": "v13", "name": "Shiva", "role": "Technical accuracy", "prompt": "Verify technical details."},
            {"id": "v14", "name": "Durga", "role": "Risk assessment", "prompt": "Identify and assess risks."},
            {"id": "v15", "name": "Lakshmi", "role": "Clarity & precision", "prompt": "Ensure clarity and precision."},
            {"id": "v16", "name": "Kubera", "role": "Financial compliance", "prompt": "Check financial law compliance."},
            {"id": "v17", "name": "Agni", "role": "Regulatory mapping", "prompt": "Map to relevant regulations."},
            {"id": "v18", "name": "Varuna", "role": "Environmental impact", "prompt": "Assess environmental implications."},
            {"id": "v19", "name": "Bhumi", "role": "Property law check", "prompt": "Verify property law aspects."},
            {"id": "v20", "name": "Aakash", "role": "Space law", "prompt": "Consider space law where applicable."}
        ]

    async def evaluate(self, responses: List[Dict], query: str, jurisdiction: str) -> Dict:
        """Run each verifier on each response, aggregate scores."""
        tasks = []
        for resp in responses:
            if 'error' in resp:
                continue
            for verifier in self.verifiers:
                tasks.append(self._verifier_judge(verifier, resp['response'], query, jurisdiction))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Group by agent
        scores = {}
        for agent_id in set(r['agent_id'] for r in responses if 'error' not in r):
            agent_results = [r for r in results if isinstance(r, dict) and r.get('agent_id') == agent_id]
            scores[agent_id] = {
                "total": len(agent_results),
                "approved": sum(1 for r in agent_results if r.get('status') == 'APPROVED'),
                "corrected": sum(1 for r in agent_results if r.get('status') == 'CORRECTED'),
                "rejected": sum(1 for r in agent_results if r.get('status') == 'REJECTED'),
                "confidence": sum(r.get('confidence_score', 0.5) for r in agent_results) / len(agent_results) if agent_results else 0,
                "feedback": [r.get('feedback') for r in agent_results if r.get('feedback')]
            }
        return {
            "jury_summary": scores,
            "detailed_verifier_responses": results
        }

    async def _verifier_judge(self, verifier: Dict, response: str, query: str, jurisdiction: str) -> Dict:
        prompt = f"""You are {verifier['name']}, {verifier['role']}. {verifier['prompt']}
        Query: {query}
        Jurisdiction: {jurisdiction}
        Response to review:
        {response[:2000]}
        Return JSON with keys: status (APPROVED/CORRECTED/REJECTED), confidence_score (0-1), feedback (string)."""
        try:
            result = await call_llm(
                system_prompt="You are a strict verifier. Return valid JSON.",
                user_prompt=prompt,
                provider="groq"
            )
            # parse JSON (simplified)
            import json
            return json.loads(result)
        except:
            return {"agent_id": "unknown", "status": "REJECTED", "confidence_score": 0, "feedback": "Parsing error"}