"""
Shakti – The Final Judge
Integrates with agents, verifiers, and RAG to deliver final verdicts.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.llm.local_model import get_llm
from core.rag.free_indian_rag import get_rag
from core.agents.orchestrator import get_orchestrator
from core.agents.registry import get_agent, list_agents

logger = logging.getLogger(__name__)


class ShaktiJudge:
    """
    The Final Judge – delivers verdicts with confidence scoring and dissenting opinions.
    """

    def __init__(self):
        self.llm = get_llm()
        self.rag = get_rag()
        self.orchestrator = get_orchestrator()
        self.name = "Shakti"
        self.version = "1.0"

    async def deliver_verdict(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """Deliver a final verdict on a legal query."""
        # 1. Orchestrate agents
        orchestration = await self.orchestrator.process(query)

        # 2. Get RAG context
        from sentence_transformers import SentenceTransformer
        from core.config import Config
        embedder = SentenceTransformer(Config.EMBEDDING_MODEL)
        query_vec = embedder.encode([query])
        docs = self.rag.search(query_vec, top_k=5) if self.rag.loaded else []

        # 3. Run verifiers
        verifier_results = await self._run_verifiers(query, orchestration)

        # 4. Synthesize verdict
        verdict = await self._synthesize_verdict(query, orchestration, verifier_results, docs)

        # 5. Calculate confidence
        confidence = await self._calculate_confidence(verifier_results, orchestration)

        # 6. Generate dissenting opinion (if confidence < 0.8)
        dissent = None
        if confidence < 0.8:
            dissent = await self._generate_dissent(query, orchestration)

        return {
            "judge": self.name,
            "version": self.version,
            "query": query,
            "verdict": verdict,
            "confidence": confidence,
            "confidence_level": self._confidence_level(confidence),
            "dissenting_opinion": dissent,
            "agents_used": orchestration.get("agents_used", []),
            "verifier_results": verifier_results,
            "sources": docs[:3] if docs else [],
            "timestamp": datetime.now().isoformat(),
            "zero_data_retention": True
        }

    async def _run_verifiers(self, query: str, orchestration: Dict) -> Dict[str, Any]:
        """Run all available verifiers."""
        results = {}
        verifier_names = [name for name in list_agents() if "Verifier" in name]

        for name in verifier_names[:5]:
            agent = get_agent(name)
            if agent:
                try:
                    result = await agent.execute({
                        "query": query,
                        "response": orchestration.get("final_answer", "")
                    })
                    results[name] = result
                except Exception as e:
                    results[name] = {"error": str(e)}

        return results

    async def _synthesize_verdict(self, query: str, orchestration: Dict,
                                  verifiers: Dict, docs: List) -> str:
        """Synthesize final verdict."""
        prompt = f"""
You are Shakti, the Final Judge. Deliver a final legal verdict.

QUERY: {query}

AGENT OUTPUTS:
{json.dumps(orchestration.get("agent_outputs", {}), indent=2, default=str)}

VERIFIER RESULTS:
{json.dumps(verifiers, indent=2, default=str)}

LEGAL CONTEXT:
{json.dumps(docs[:3], indent=2, default=str)}

Provide a balanced, fair, and legally sound verdict.
"""
        return self.llm.generate(prompt, max_new_tokens=1000)

    async def _calculate_confidence(self, verifiers: Dict, orchestration: Dict) -> float:
        """Calculate confidence score."""
        confidence = 0.7
        for name, result in verifiers.items():
            if result.get("status") == "pass":
                confidence += 0.05
            elif result.get("status") == "fail":
                confidence -= 0.1
            elif result.get("score"):
                confidence += (result["score"] - 50) / 100

        agent_count = len(orchestration.get("agents_used", []))
        confidence += min(agent_count * 0.01, 0.1)

        return max(0.0, min(1.0, confidence))

    def _confidence_level(self, confidence: float) -> str:
        if confidence >= 0.9:
            return "Very High"
        elif confidence >= 0.75:
            return "High"
        elif confidence >= 0.6:
            return "Medium"
        elif confidence >= 0.4:
            return "Low"
        else:
            return "Very Low"

    async def _generate_dissent(self, query: str, orchestration: Dict) -> Optional[str]:
        """Generate a dissenting opinion."""
        prompt = f"""
You are a dissenting judge. Provide a counter-argument.

QUERY: {query}

MAJORITY VIEW:
{orchestration.get("final_answer", "")}

Provide a reasoned dissenting opinion.
"""
        return self.llm.generate(prompt, max_new_tokens=500)


# Singleton
_shakti = None

def get_shakti():
    global _shakti
    if _shakti is None:
        _shakti = ShaktiJudge()
    return _shakti