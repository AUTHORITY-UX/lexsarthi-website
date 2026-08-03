"""
core/llm/providers.py - 6 LLM Providers (Sarvam, OpenAI, Gemini, Groq, DeepSeek, OpenRouter)
"""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Dict, Optional
import httpx
from core.config import settings

@dataclass
class LLMMessage:
    role: str
    content: str
    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""
    def __bool__(self) -> bool:
        return self.success and bool(self.content and self.content.strip())

class BaseLLMProvider:
    name: str = "base"
    base_url: str = ""
    default_model: str = ""
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self._client = None
    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                headers=self._headers(),
            )
        return self._client
    def _headers(self) -> dict:
        raise NotImplementedError
    async def chat(self, messages, *, model=None, max_tokens=None, temperature=None) -> LLMResponse:
        raise NotImplementedError
    async def chat_stream(self, messages, *, model=None, max_tokens=None, temperature=None):
        raise NotImplementedError
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    @staticmethod
    def _safe(content, provider, model, usage, latency_ms) -> LLMResponse:
        if content is None:
            return LLMResponse(content="", provider=provider, model=model,
                               usage=usage, latency_ms=latency_ms, success=False, error="null_content")
        content = str(content).strip()
        if not content:
            return LLMResponse(content="", provider=provider, model=model,
                               usage=usage, latency_ms=latency_ms, success=False, error="empty_content")
        return LLMResponse(content=content, provider=provider, model=model,
                          usage=usage, latency_ms=latency_ms, success=True)

class SarvamProvider(BaseLLMProvider):
    name = "sarvam"
    base_url = "https://api.sarvam.ai/v1"
    default_model = "sarvam-105b"
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    async def chat(self, messages, *, model=None, max_tokens=None, temperature=None):
        model = model or self.default_model
        max_tokens = max_tokens or 1024
        temperature = temperature if temperature is not None else 0.3
        client = await self.get_client()
        t0 = time.monotonic()
        try:
            resp = await client.post(f"{self.base_url}/chat/completions", json={
                "model": model,
                "messages": [m.to_dict() for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
            })
            latency = (time.monotonic() - t0) * 1000
            if resp.status_code != 200:
                return LLMResponse(content="", provider=self.name, model=model,
                                   latency_ms=latency, success=False, error=f"http_{resp.status_code}")
            data = resp.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            return self._safe(content, self.name, model, data.get("usage", {}), latency)
        except Exception as exc:
            return LLMResponse(content="", provider=self.name, model=model,
                               latency_ms=(time.monotonic() - t0) * 1000,
                               success=False, error=str(exc)[:200])

class OpenAIProvider(BaseLLMProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o"
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    async def chat(self, messages, *, model=None, max_tokens=None, temperature=None):
        model = model or self.default_model
        max_tokens = max_tokens or 1024
        temperature = temperature if temperature is not None else 0.3
        client = await self.get_client()
        t0 = time.monotonic()
        try:
            resp = await client.post(f"{self.base_url}/chat/completions", json={
                "model": model,
                "messages": [m.to_dict() for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
            })
            latency = (time.monotonic() - t0) * 1000
            if resp.status_code != 200:
                return LLMResponse(content="", provider=self.name, model=model,
                                   latency_ms=latency, success=False, error=f"http_{resp.status_code}")
            data = resp.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            return self._safe(content, self.name, model, data.get("usage", {}), latency)
        except Exception as exc:
            return LLMResponse(content="", provider=self.name, model=model,
                               latency_ms=(time.monotonic() - t0) * 1000,
                               success=False, error=str(exc)[:200])

class GeminiProvider(BaseLLMProvider):
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    default_model = "gemini-1.5-flash"
    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}
    async def chat(self, messages, *, model=None, max_tokens=None, temperature=None):
        model = model or self.default_model
        max_tokens = max_tokens or 1024
        temperature = temperature if temperature is not None else 0.3
        client = await self.get_client()
        t0 = time.monotonic()
        try:
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
            body = {
                "contents": [{"role": "user", "parts": [{"text": m.content}]} for m in messages if m.role != "system"],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
            }
            resp = await client.post(url, json=body)
            latency = (time.monotonic() - t0) * 1000
            if resp.status_code != 200:
                return LLMResponse(content="", provider=self.name, model=model,
                                   latency_ms=latency, success=False, error=f"http_{resp.status_code}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return LLMResponse(content="", provider=self.name, model=model,
                                   latency_ms=latency, success=False, error="no_candidates")
            parts = candidates[0].get("content", {}).get("parts", [])
            content = " ".join(p.get("text", "") for p in parts)
            return self._safe(content, self.name, model, data.get("usageMetadata", {}), latency)
        except Exception as exc:
            return LLMResponse(content="", provider=self.name, model=model,
                               latency_ms=(time.monotonic() - t0) * 1000,
                               success=False, error=str(exc)[:200])

class GroqProvider(OpenAIProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"

class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"
    base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"

class OpenRouterProvider(OpenAIProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    default_model = "mistralai/mistral-large"

PROVIDER_CLASSES = {
    "sarvam": SarvamProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
    "openrouter": OpenRouterProvider,
}

MODEL_REGISTRY = {
    "sarvam-105b": ("sarvam", "sarvam-105b"),
    "sarvam-30b": ("sarvam", "sarvam-30b"),
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "gemini-1.5-flash": ("gemini", "gemini-1.5-flash"),
    "gemini-1.5-pro": ("gemini", "gemini-1.5-pro"),
    "llama-3.3-70b": ("groq", "llama-3.3-70b-versatile"),
    "llama-3.1-8b": ("groq", "llama-3.1-8b-instant"),
    "deepseek-chat": ("deepseek", "deepseek-chat"),
    "deepseek-reasoner": ("deepseek", "deepseek-reasoner"),
    "mistral-large": ("openrouter", "mistralai/mistral-large"),
}

_provider_instances = {}

async def get_provider(name: str) -> BaseLLMProvider:
    if name in _provider_instances:
        return _provider_instances[name]
    if name not in PROVIDER_CLASSES:
        raise ValueError(f"Unknown LLM provider: {name}")
    key_map = {
        "sarvam": settings.SARVAM_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "deepseek": settings.DEEPSEEK_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
    }
    api_key = key_map.get(name, "")
    if not api_key:
        raise RuntimeError(f"Provider '{name}' has no API key configured.")
    provider = PROVIDER_CLASSES[name](api_key=api_key)
    _provider_instances[name] = provider
    return provider

async def close_all_providers():
    for p in _provider_instances.values():
        await p.close()
    _provider_instances.clear()