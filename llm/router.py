"""
core/llm/router.py
==================
The intelligent LLM router — decides which model to use, handles fallbacks,
caches responses, and streams output.

  1. Complexity classification — simple/medium/complex prompts route to
     different models (kills the 100s latency: 70% of queries use Groq 8B).
  2. Fallback chains — if Sarvam times out, fall back to OpenAI, then Groq.
     Never returns null.
  3. Redis caching — identical questions return cached answers instantly.
  4. Streaming — SSE streaming for chat endpoints (first token <1s).
  5. Null-guard — every path returns a valid LLMResponse, never None.
"""

from __future__ import annotations

import hashlib
import json
import time
import logging
from typing import AsyncIterator, List, Optional

from core.config import settings
from core.llm.providers import (
    LLMMessage, LLMResponse, get_provider, close_all_providers, MODEL_REGISTRY,
)

logger = logging.getLogger(__name__)


class ComplexityClassifier:
    """Heuristic classifier (no LLM needed — fast, free, deterministic)."""

    COMPLEX_KEYWORDS = [
        "constitutional", "supreme court", "high court", "judgment",
        "precedent", "writ petition", "fundamental rights", "interpret",
        "analyse", "analyze", "compare", "evaluate", "multi-party",
        "cross-examination", "appeal", "revision", "detailed", "comprehensive",
    ]
    SIMPLE_KEYWORDS = [
        "what is", "define", "meaning of", "section", "act",
        "hello", "hi", "thanks", "help",
    ]

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
    "simple": [
        ("groq", "llama-3.1-8b-instant"),
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-1.5-flash"),
        ("sarvam", "sarvam-30b"),
    ],
    "medium": [
        ("sarvam", "sarvam-30b"),
        ("openai", "gpt-4o-mini"),
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-1.5-flash"),
    ],
    "complex": [
        ("sarvam", "sarvam-105b"),
        ("openai", "gpt-4o"),
        ("deepseek", "deepseek-reasoner"),
        ("gemini", "gemini-1.5-pro"),
    ],
}


class LLMCache:
    """Redis-backed response cache. Falls back to in-memory if Redis is down."""

    def __init__(self):
        self._redis = None
        self._memory: dict[str, tuple[str, float]] = {}
        self._available = False

    async def init(self, redis_client):
        self._redis = redis_client
        if redis_client:
            try:
                await redis_client.ping()
                self._available = True
                logger.info("LLM cache: Redis connected")
            except Exception:
                self._available = False
                logger.warning("LLM cache: Redis unavailable, using in-memory")

    def _key(self, messages, model, max_tokens) -> str:
        raw = json.dumps([{"role": m.role, "content": m.content} for m in messages], sort_keys=True) + f"|{model}|{max_tokens}"
        return f"{settings.CACHE_PREFIX}llm:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get(self, messages, model, max_tokens) -> Optional[LLMResponse]:
        key = self._key(messages, model, max_tokens)
        if self._available and self._redis:
            try:
                raw = await self._redis.get(key)
                if raw:
                    return LLMResponse(**json.loads(raw))
            except Exception:
                pass
        else:
            if key in self._memory:
                val, expires = self._memory[key]
                if time.time() < expires:
                    return LLMResponse(**json.loads(val))
                del self._memory[key]
        return None

    async def set(self, messages, model, max_tokens, response: LLMResponse):
        key = self._key(messages, model, max_tokens)
        data = json.dumps({
            "content": response.content, "provider": response.provider,
            "model": response.model, "usage": response.usage,
            "latency_ms": response.latency_ms, "success": response.success,
            "error": response.error,
        })
        ttl = settings.CACHE_TTL_SECONDS
        if self._available and self._redis:
            try:
                await self._redis.setex(key, ttl, data)
            except Exception:
                pass
        else:
            self._memory[key] = (data, time.time() + ttl)

    async def close(self):
        if self._redis:
            await self._redis.aclose()


class LLMRouter:
    def __init__(self):
        self.classifier = ComplexityClassifier()
        self.cache = LLMCache()
        self._initialized = False

    async def init(self, redis_client=None):
        await self.cache.init(redis_client)
        self._initialized = True
        logger.info("LLM router initialized. Providers: %s", settings.available_llm_providers)

    def _get_chain(self, complexity, forced_model=None):
        if forced_model:
            provider = None
            for friendly, (prov, mid) in MODEL_REGISTRY.items():
                if friendly == forced_model or mid == forced_model:
                    provider = prov
                    forced_model = mid
                    break
            if provider:
                chain = [(provider, forced_model)]
                for p, m in FALLBACK_CHAINS.get(complexity, []):
                    if (p, m) not in chain:
                        chain.append((p, m))
                return chain
        return FALLBACK_CHAINS.get(complexity, FALLBACK_CHAINS["medium"])

    def _max_tokens_for(self, complexity) -> int:
        return {"simple": settings.LLM_MAX_TOKENS_CHAT,
                "medium": settings.LLM_MAX_TOKENS_DEFAULT,
                "complex": settings.LLM_MAX_TOKENS_COMPLEX}.get(complexity, settings.LLM_MAX_TOKENS_DEFAULT)

    async def chat(self, messages, *, model=None, complexity=None, max_tokens=None,
                   temperature=None, use_cache=True) -> LLMResponse:
        if complexity is None:
            complexity = self.classifier.classify(messages)
        chain = self._get_chain(complexity, forced_model=model)
        if not max_tokens:
            max_tokens = self._max_tokens_for(complexity)

        if use_cache:
            for provider_name, model_id in chain:
                cached = await self.cache.get(messages, model_id, max_tokens)
                if cached and cached.success:
                    logger.info("Cache HIT: %s/%s", provider_name, model_id)
                    cached.error = "cache_hit"
                    return cached

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
                    if use_cache:
                        await self.cache.set(messages, model_id, max_tokens, response)
                    logger.info("LLM success: %s latency=%.0fms", provider_name, response.latency_ms)
                    return response
                else:
                    errors.append(f"{provider_name}/{model_id}: {response.error}")
                    logger.warning("LLM failed: %s error=%s", provider_name, response.error)
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
                collected = []
                async for chunk in provider.chat_stream(messages, model=model_id,
                                                         max_tokens=max_tokens, temperature=temperature):
                    collected.append(chunk)
                    yield chunk
                if collected:
                    return
                continue
            except NotImplementedError:
                response = await provider.chat(messages, model=model_id,
                                               max_tokens=max_tokens, temperature=temperature)
                if response.success and response.content:
                    yield response.content
                    return
            except Exception as exc:
                logger.warning("Stream error from %s: %s", provider_name, exc)
                continue
        yield "I apologise — all language models are temporarily unavailable."

    async def close(self):
        await self.cache.close()
        await close_all_providers()


_router: Optional[LLMRouter] = None

def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
