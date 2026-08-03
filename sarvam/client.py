"""
sarvam/client.py
=================
Backward-compatible Sarvam client that delegates to the multi-LLM router.

This file exists so that any code importing `from sarvam.client import SarvamClient`
keeps working. It now uses the LLM router internally, which means:
  - Falls back to OpenAI/Groq/Gemini if Sarvam is down
  - Never returns None (null cascade fix)
  - 30s timeout (not 100s)
  - Redis cached

If you want the raw provider without the router, use:
    from core.llm.providers import SarvamProvider
"""

from __future__ import annotations

import logging
from typing import Optional

from core.config import settings
from core.llm import LLMMessage, LLMResponse, get_router, get_provider

logger = logging.getLogger(__name__)


class SarvamClient:
    """
    Drop-in replacement for the old SarvamClient.
    Uses the multi-LLM router under the hood for fallback + caching.
    """

    def __init__(self, model: str = "sarvam-105b"):
        self.model = model
        self.router = get_router()

    async def chat(self, prompt: str, *, system: str = "", max_tokens: int = 512,
                   temperature: float = 0.3) -> str:
        """Simple chat — returns a string, never None."""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))

        response = await self.router.chat(
            messages, model=self.model, max_tokens=max_tokens,
            temperature=temperature, use_cache=True,
        )
        # Null guard — return empty string instead of None
        return response.content if response.content else ""

    async def chat_with_messages(self, messages, *, max_tokens: int = 512,
                                  temperature: float = 0.3) -> LLMResponse:
        """Chat with full message list — returns LLMResponse."""
        return await self.router.chat(
            messages, model=self.model, max_tokens=max_tokens,
            temperature=temperature,
        )

    async def stream(self, prompt: str, *, system: str = "", max_tokens: int = 512):
        """Streaming chat — yields string chunks."""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))
        async for chunk in self.router.stream(messages, model=self.model, max_tokens=max_tokens):
            yield chunk


async def get_sarvam_client(model: str = "sarvam-105b") -> SarvamClient:
    """Factory for SarvamClient."""
    return SarvamClient(model=model)


# Legacy function names for backward compatibility
async def call_sarvam(prompt: str, **kwargs) -> str:
    """Legacy: direct Sarvam call via router. Returns string, never None."""
    client = SarvamClient()
    return await client.chat(prompt, **kwargs)
