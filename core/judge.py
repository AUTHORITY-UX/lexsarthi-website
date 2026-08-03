"""
unknown_verdict.core.judge
===========================
AI Judge — renders verdicts using multi-LLM input + 15 verifiers.

Critical fix: the judge now guards against null responses at every step.
Previously, a null Sarvam response crashed the judge with:
  AttributeError: 'NoneType' object has no attribute 'lower'

Now:
  1. Gets a response from the LLM router (which never returns null)
  2. Guards against empty content before any string operations
  3. Runs verifiers (which also guard against null)
  4. Renders a structured verdict with confidence score
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from unknown_verdict.core.llm import LLMMessage, get_router
from unknown_verdict.core.verifiers import verify_summary, _safe_text
from unknown_verdict.core.config import settings

logger = logging.getLogger(__name__)


class AIJudge:
    """
    The AI Judge renders structured legal verdicts with confidence scoring.

    It uses the LLM router for generation and 15 verifiers for validation.
    """

    def __init__(self):
        self.mode = settings.VERDICT_ENGINE_MODE
        self.router = get_router()

    async def render_verdict(
        self,
        query: str,
        *,
        mode: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        """
        Render a verdict on a legal query.

        Returns a structured dict — never returns None.
        """
        mode = mode or self.mode

        # 1. Generate verdict via LLM router
        messages = [
            LLMMessage(role="system", content=(
                f"You are the AI Judge of Unknown Verdict, operating in {mode} mode.\n"
                f"Mode definitions:\n"
                f"  strict:   Requires high legal certainty, cautious ruling\n"
                f"  balanced: Weights both sides fairly, standard of proof\n"
                f"  lenient:  Favors the party with stronger narrative\n\n"
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

        # 2. Null guard — the core fix
        content = _safe_text(response.content)
        if not content.strip():
            logger.warning("AI Judge: LLM returned empty response, returning fallback verdict")
            return {
                "verdict": "undetermined",
                "reasoning": "The AI Judge was unable to render a verdict due to "
                            "an unavailable language model. Please try again.",
                "confidence": 0,
                "precedents": [],
                "dissent": None,
                "provider": response.provider,
                "model": response.model,
                "verified": False,
                "verification": None,
            }

        # 3. Run verifiers (null-safe)
        verification = verify_summary(query, content)

        # 4. Extract confidence if present
        confidence = self._extract_confidence(content)

        # 5. Structure the verdict
        return {
            "verdict": content,
            "mode": mode,
            "confidence": confidence,
            "verification": verification,
            "verified": verification.get("avg_score", 0) > 0.5,
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
        }

    def _extract_confidence(self, content: str) -> int:
        """Try to extract a confidence score from the LLM output."""
        import re
        # Look for "CONFIDENCE: 85" or "confidence: 85/100" patterns
        patterns = [
            r"CONFIDENCE:\s*(\d{1,3})",
            r"confidence:\s*(\d{1,3})",
            r"Confidence:\s*(\d{1,3})",
            r"(\d{1,3})\s*/\s*100",
        ]
        for p in patterns:
            match = re.search(p, content)
            if match:
                val = int(match.group(1))
                return min(max(val, 0), 100)  # clamp 0-100
        # Default confidence based on verification score
        return 50  # neutral if not found

    async def compare_models(self, query: str) -> dict:
        """Get verdicts from all available models and compare."""
        from unknown_verdict.core.llm import get_provider
        results = {}
        for provider_name in settings.available_llm_providers:
            try:
                provider = await get_provider(provider_name)
                messages = [
                    LLMMessage(role="system", content="You are an AI legal judge. Render a verdict."),
                    LLMMessage(role="user", content=query),
                ]
                response = await provider.chat(messages, max_tokens=512)

                # Null guard for each provider
                results[provider_name] = {
                    "verdict": response.content or "No verdict rendered",
                    "success": response.success,
                    "latency_ms": response.latency_ms,
                }
            except Exception as exc:
                results[provider_name] = {"error": str(exc)[:200]}
        return {"query": query, "comparisons": results}


# Singleton
judge = AIJudge()
