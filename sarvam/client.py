"""
Sarvam AI Integration Client
=============================
Handles communication with Sarvam AI's 105B and 30B models.
- 105B model: Complex legal reasoning, AI Judge decisions
- 30B model: Fast responses, agent interactions
"""
from __future__ import annotations

import asyncio
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ..config import settings


class SarvamModel(str, Enum):
    """Available Sarvam AI models."""
    SARVAM_105B = "sarvam-105b"
    SARVAM_30B = "sarvam-30b"


@dataclass
class SarvamMessage:
    """Chat message structure."""
    role: str  # system, user, assistant
    content: str


@dataclass
class SarvamRequest:
    """Request payload for Sarvam AI."""
    model: SarvamModel
    messages: List[SarvamMessage]
    temperature: float = 0.3
    max_tokens: int = 4096
    top_p: float = 0.9
    stream: bool = False

    def to_dict(self) -> dict:
        return {
            "model": self.model.value,
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stream": self.stream,
        }


@dataclass
class SarvamResponse:
    """Response from Sarvam AI."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class SarvamUsageStats:
    """Track Sarvam API usage statistics."""
    total_requests: int = 0
    total_105b_requests: int = 0
    total_30b_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_request_at: Optional[float] = None

    def record(self, response: SarvamResponse) -> None:
        self.total_requests += 1
        if "105b" in response.model:
            self.total_105b_requests += 1
        else:
            self.total_30b_requests += 1
        self.total_tokens += response.usage.get("total_tokens", 0)
        if not response.success:
            self.total_errors += 1
        # Rolling average latency
        n = self.total_requests
        self.avg_latency_ms = ((self.avg_latency_ms * (n - 1)) + response.latency_ms) / n
        self.last_request_at = time.time()

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_105b_requests": self.total_105b_requests,
            "total_30b_requests": self.total_30b_requests,
            "total_tokens": self.total_tokens,
            "total_errors": self.total_errors,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "last_request_at": self.last_request_at,
        }


class SarvamClient:
    """
    Async client for Sarvam AI API.
    Supports chat completions, streaming, and legal-specific system prompts.
    """

    def __init__(self) -> None:
        self.base_url = settings.SARVAM_BASE_URL.rstrip("/")
        self.api_key = settings.SARVAM_API_KEY
        self.timeout = settings.SARVAM_TIMEOUT
        self.max_retries = settings.SARVAM_MAX_RETRIES
        self.usage = SarvamUsageStats()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        """Check if Sarvam API key is configured."""
        return settings.is_sarvam_configured

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Source": "unknown-verdict-v40",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    async def _call_with_retry(
        self,
        request: SarvamRequest,
    ) -> SarvamResponse:
        """Call Sarvam API with exponential backoff retry."""
        client = await self._get_client()
        last_error: Optional[str] = None

        for attempt in range(self.max_retries):
            try:
                start = time.time()
                resp = await client.post("/chat/completions", json=request.to_dict())
                latency = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    content = ""
                    if "choices" in data and data["choices"]:
                        msg = data["choices"][0].get("message", {})
                        content = msg.get("content", "") or ""
                    # Sarvam sometimes returns null content on timeout — convert to empty string
                    if content is None:
                        content = ""
                    usage = data.get("usage", {})
                    # If content is empty, treat as a soft failure
                    is_success = bool(content and content.strip())
                    response = SarvamResponse(
                        content=content or "",
                        model=request.model.value,
                        usage=usage,
                        latency_ms=latency,
                        success=is_success,
                        error=None if is_success else "Empty response from Sarvam API",
                        raw=data,
                    )
                    self.usage.record(response)
                    return response

                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                    # 4xx errors are not retryable
                    if 400 <= resp.status_code < 500:
                        break

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_error = str(e)
            except Exception as e:
                last_error = f"Unexpected error: {e}"

            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        # All retries failed
        response = SarvamResponse(
            content="",
            model=request.model.value,
            success=False,
            error=last_error,
        )
        self.usage.record(response)
        return response

    async def chat(
        self,
        messages: List[SarvamMessage | Dict[str, str]],
        model: SarvamModel = SarvamModel.SARVAM_30B,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> SarvamResponse:
        """Send a chat completion request."""
        # Normalize messages
        normalized: List[SarvamMessage] = []
        for m in messages:
            if isinstance(m, dict):
                normalized.append(SarvamMessage(role=m["role"], content=m["content"]))
            else:
                normalized.append(m)

        request = SarvamRequest(
            model=model,
            messages=normalized,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return await self._call_with_retry(request)

    async def reason(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> SarvamResponse:
        """
        Complex legal reasoning using the 105B model.
        Used by the AI Judge and for high-stakes legal analysis.
        """
        messages: List[SarvamMessage] = []
        if system_prompt:
            messages.append(SarvamMessage(role="system", content=system_prompt))
        messages.append(SarvamMessage(role="user", content=prompt))
        return await self.chat(
            messages=messages,
            model=SarvamModel.SARVAM_105B,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def fast_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> SarvamResponse:
        """Fast response using the 30B model for quick queries."""
        messages: List[SarvamMessage] = []
        if system_prompt:
            messages.append(SarvamMessage(role="system", content=system_prompt))
        messages.append(SarvamMessage(role="user", content=prompt))
        return await self.chat(
            messages=messages,
            model=SarvamModel.SARVAM_30B,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def stream_chat(
        self,
        messages: List[SarvamMessage | Dict[str, str]],
        model: SarvamModel = SarvamModel.SARVAM_30B,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens."""
        normalized: List[SarvamMessage] = []
        for m in messages:
            if isinstance(m, dict):
                normalized.append(SarvamMessage(role=m["role"], content=m["content"]))
            else:
                normalized.append(m)

        request = SarvamRequest(
            model=model,
            messages=normalized,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        client = await self._get_client()
        async with client.stream(
            "POST", "/chat/completions", json=request.to_dict()
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk.get("choices"):
                            delta = chunk["choices"][0].get("delta", {})
                            if delta.get("content"):
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> dict:
        """Check Sarvam AI service health."""
        if not self.is_configured:
            return {
                "status": "not_configured",
                "configured": False,
                "message": "Sarvam API key not set. Set SARVAM_API_KEY in environment.",
                "models": {"105b": "unavailable", "30b": "unavailable"},
            }
        return {
            "status": "operational",
            "configured": True,
            "message": "Sarvam AI integration is active.",
            "base_url": self.base_url,
            "models": {
                "105b": {
                    "name": settings.SARVAM_105B_MODEL,
                    "use": "complex legal reasoning, AI Judge",
                    "max_tokens": 8192,
                },
                "30b": {
                    "name": settings.SARVAM_30B_MODEL,
                    "use": "fast responses, agent interactions",
                    "max_tokens": 4096,
                },
            },
            "usage": self.usage.to_dict(),
        }

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton client
sarvam_client = SarvamClient()
