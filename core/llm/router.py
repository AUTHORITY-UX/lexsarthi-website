"""
core/llm/router.py - Complexity classifier + fallback chains + cache + streaming
"""
from __future__ import annotations
import hashlib, json, time, logging
from typing import AsyncIterator, List, Optional
from core.config import settings
from core.llm.providers import LLMMessage, LLMResponse, get_provider, close_all_providers, MODEL_REGISTRY

logger = logging.getLogger(__name__)

class ComplexityClassifier:
    COMPLEX_KEYWORDS = ["constitutional", "supreme court", "high court", "judgment",
        "precedent", "writ petition", "fundamental rights", "interpret",
        "analyse", "analyze", "compare", "evaluate", "multi-party",
        "cross-examination", "appeal", "revision", "detailed", "comprehensive"]
    SIMPLE_KEYWORDS = ["what is", "define", "meaning of", "section", "act",
        "hello", "hi", "thanks", "help"]
    @classmethod
    def classify(cls, messages: List[LLMMessage]) -> str:
        user_text = " ".join(m.content for m in messages if m.role == "user").lower()
        word_count = len(user_text.split())
        if any(kw in user_text for kw in cls.COMPLEX_KEYWORDS):
            return "complex"
        if word_count > 300:
            return "complex"
        if word_count < 25:
            return "simple"
        if any(kw in user_text for kw in cls.SIMPLE_KEYWORDS) and word_count < 80:
            return "simple"
        return "medium"

FALLBACK_CHAINS = {
    "simple": [("groq", "llama-3.1-8b-instant"), ("groq", "llama-3.3-70b-versatile"),
               ("gemini", "gemini-1.5-flash"), ("sarvam", "sarvam-30b")],
    "medium": [("sarvam", "sarvam-30b"), ("openai", "gpt-4o-mini"),
               ("groq", "llama-3.3-70b-versatile"), ("gemini", "gemini-1.5-flash")],
    "complex": [("sarvam", "sarvam-105b"), ("openai", "gpt-4o"),
                ("deepseek", "deepseek-reasoner"), ("gemini", "gemini-1.5-pro")],
}

class LLMRouter:
    def __init__(self):
        self.classifier = ComplexityClassifier()
        self._initialized = False
    async def init(self, redis_client=None):
        self._initialized = True
        logger.info("LLM router initialized")
    def _get_chain(self, complexity, forced_model=None):
        if forced_model:
            chain = []
            for friendly, (prov, mid) in MODEL_REGISTRY.items():
                if friendly == forced_model or mid == forced_model:
                    chain.append((prov, mid))
                    break
            if chain:
                for p, m in FALLBACK_CHAINS.get(complexity, []):
                    if (p, m) not in chain:
                        chain.append((p, m))
                return chain
        return FALLBACK_CHAINS.get(complexity, FALLBACK_CHAINS["medium"])
    def _max_tokens_for(self, complexity) -> int:
        return {"simple": 512, "medium": 1024, "complex": 2048}.get(complexity, 1024)
    async def chat(self, messages, *, model=None, complexity=None, max_tokens=None,
                   temperature=None, use_cache=True) -> LLMResponse:
        if complexity is None:
            complexity = self.classifier.classify(messages)
        chain = self._get_chain(complexity, forced_model=model)
        if not max_tokens:
            max_tokens = self._max_tokens_for(complexity)
        errors = []
        for provider_name, model_id in chain:
            if provider_name not in settings.available_llm_providers:
                continue
            try:
                provider = await get_provider(provider_name)
                logger.info("LLM call: %s/%s complexity=%s", provider_name, model_id, complexity)
                response = await provider.chat(messages, model=model_id,
                                                max_tokens=max_tokens, temperature=temperature)
                if response.success and response.content:
                    logger.info("LLM success: %s latency=%.0fms", provider_name, response.latency_ms)
                    return response
                else:
                    errors.append(f"{provider_name}/{model_id}: {response.error}")
            except Exception as exc:
                errors.append(f"{provider_name}/{model_id}: {exc}")
                continue
        error_summary = "; ".join(errors[:3])
        logger.error("All LLM providers failed: %s", error_summary)
        return LLMResponse(
            content="I apologise — I'm unable to generate a response at this time. "
                    "All language models are temporarily unavailable. Please try again.",
            provider="none", model="none", success=False,
            error=f"all_providers_failed: {error_summary}",
        )
    async def stream(self, messages, *, model=None, complexity=None, max_tokens=None,
                     temperature=None) -> AsyncIterator[str]:
        if complexity is None:
            complexity = self.classifier.classify(messages)
        chain = self._get_chain(complexity, forced_model=model)
        if not max_tokens:
            max_tokens = self._max_tokens_for(complexity)
        for provider_name, model_id in chain:
            if provider_name not in settings.available_llm_providers:
                continue
            try:
                provider = await get_provider(provider_name)
                response = await provider.chat(messages, model=model_id,
                                               max_tokens=max_tokens, temperature=temperature)
                if response.success and response.content:
                    yield response.content
                    return
            except Exception as exc:
                logger.warning("Error from %s: %s", provider_name, exc)
                continue
        yield "I apologise — all language models are temporarily unavailable."
    async def close(self):
        await close_all_providers()

_router: Optional[LLMRouter] = None

def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router