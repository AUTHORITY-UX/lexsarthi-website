"""
core/judge.py
==============
AI Judge — renders verdicts using multi-LLM input + 15 verifiers.

Critical fix: guards against null responses at every step.
Previously a null Sarvam response crashed with:
  AttributeError: 'NoneType' object has no attribute 'lower'
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from core.llm import LLMMessage, get_router
from core.verifiers import verify_summary, _safe_text
from core.config import settings

logger = logging.getLogger(__name__)


class AIJudge:
    def __init__(self):
        self.mode = settings.VERDICT_ENGINE_MODE
        self.router = get_router()

    async def render_verdict(self, query: str, *, mode: Optional[str] = None,
                              model: Optional[str] = None) -> dict:
        mode = mode or self.mode
        messages = [
            LLMMessage(role="system", content=(
                f"You are the AI Judge of Unknown Verdict, operating in {mode} mode.\n"
                "Render a structured verdict with:\n"
                "1. RULING: (in favour of plaintiff/defendant/neither)\n"
                "2. REASONING: (detailed legal reasoning)\n"
                "3. CONFIDENCE: (0-100 integer)\n"
                "4. KEY_PRECEDENTS: (relevant case law)\n"
                "5. DISSENT: (dissenting opinion if any)"
            )),
            LLMMessage(role="user", content=query),
        ]
        response = await self.router.chat(messages, model=model, complexity="complex")

        # Null guard — the core fix
        content = _safe_text(response.content)
        if not content.strip():
            logger.warning("AI Judge: LLM returned empty response, returning fallback")
            return {
                "verdict": "undetermined",
                "reasoning": "The AI Judge was unable to render a verdict due to "
                            "an unavailable language model. Please try again.",
                "confidence": 0, "precedents": [], "dissent": None,
                "provider": response.provider, "model": response.model,
                "verified": False, "verification": None,
            }

        verification = verify_summary(query, content)
        confidence = self._extract_confidence(content)

        return {
            "verdict": content, "mode": mode, "confidence": confidence,
            "verification": verification, "verified": verification.get("avg_score", 0) > 0.5,
            "provider": response.provider, "model": response.model,
            "latency_ms": response.latency_ms,
        }

    def _extract_confidence(self, content: str) -> int:
        patterns = [r"CONFIDENCE:\s*(\d{1,3})", r"confidence:\s*(\d{1,3})",
                    r"Confidence:\s*(\d{1,3})", r"(\d{1,3})\s*/\s*100"]
        for p in patterns:
            match = re.search(p, content)
            if match:
                return min(max(int(match.group(1)), 0), 100)
        return 50

    async def compare_models(self, query: str) -> dict:
        from core.llm import get_provider
        results = {}
        for pname in settings.available_llm_providers:
            try:
                provider = await get_provider(pname)
                messages = [
                    LLMMessage(role="system", content="You are an AI legal judge. Render a verdict."),
                    LLMMessage(role="user", content=query),
                ]
                response = await provider.chat(messages, max_tokens=512)
                results[pname] = {"verdict": response.content or "No verdict rendered",
                                  "success": response.success, "latency_ms": response.latency_ms}
            except Exception as exc:
                results[pname] = {"error": str(exc)[:200]}
        return {"query": query, "comparisons": results}


judge = AIJudge()
