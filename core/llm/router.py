# core/llm/router.py
# Complete LLM Router with Ollama Support

import time
import asyncio
import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache

from core.config import settings
from core.llm.ollama_provider import OllamaProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

# ─── LLM ROUTER ──────────────────────────────────────────────────────

class LLMRouter:
    """Routes LLM requests to the best available provider"""
    
    def __init__(self):
        self.providers: Dict[str, Any] = {}
        self.default_provider: Optional[str] = None
        self.fallback_chain: List[str] = []
        self._initialized = False
    
    async def init(self, redis_client=None):
        """Initialize all providers"""
        if self._initialized:
            return
        
        # Ollama (primary – local, free)
        if settings.OLLAMA_ENABLED:
            self.providers["ollama"] = OllamaProvider(settings.OLLAMA_MODEL)
            self.default_provider = "ollama"
            logger.info("✅ Ollama provider registered (model: %s)", settings.OLLAMA_MODEL)
        
        # Other providers can be added here
        # But for now, we only use Ollama for local development
        
        self.fallback_chain = ["ollama"]
        self._initialized = True
        
        if not self.providers:
            logger.warning("⚠️ No LLM providers available!")
    
    async def chat(self, messages: List[LLMMessage], model: Optional[str] = None, 
                   temperature: float = 0.7, max_tokens: int = 1000, 
                   complexity: Optional[str] = None, **kwargs) -> LLMResponse:
        """Route chat to the best available provider"""
        
        # Use specified model or default
        model = model or settings.OLLAMA_MODEL
        
        # Try primary provider first
        primary = self.default_provider
        if primary and primary in self.providers:
            try:
                start_time = time.time()
                response = await self.providers[primary].chat(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
                if response.success:
                    return response
                else:
                    logger.warning(f"Primary provider {primary} failed: {response.error}")
            except Exception as e:
                logger.warning(f"Primary provider {primary} error: {e}")
        
        # Try fallback providers
        for fallback in self.fallback_chain:
            if fallback == primary:
                continue
            if fallback in self.providers:
                try:
                    response = await self.providers[fallback].chat(
                        messages, temperature=temperature, max_tokens=max_tokens
                    )
                    if response.success:
                        return response
                except Exception as e:
                    logger.warning(f"Fallback provider {fallback} error: {e}")
        
        # All providers failed
        return LLMResponse(
            content="All LLM providers are currently unavailable. Please try again later.",
            provider="none",
            model="none",
            success=False,
            error="No provider available"
        )
    
    async def stream(self, messages: List[LLMMessage], model: Optional[str] = None,
                     temperature: float = 0.7, max_tokens: int = 1000, **kwargs):
        """Stream from the best available provider"""
        
        model = model or settings.OLLAMA_MODEL
        provider_name = self.default_provider
        
        if provider_name in self.providers:
            async for chunk in self.providers[provider_name].stream(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                yield chunk
        else:
            yield "No streaming provider available"
    
    def get_provider(self, name: str):
        """Get a specific provider by name"""
        return self.providers.get(name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
    
    def is_healthy(self) -> bool:
        """Check if router is healthy"""
        return self._initialized and len(self.providers) > 0


# ─── SINGLETON INSTANCE ────────────────────────────────────────────

_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Get the singleton LLM router instance"""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def reset_router():
    """Reset the router (useful for testing)"""
    global _router
    _router = None


# ─── CONVENIENCE FUNCTIONS ─────────────────────────────────────────

async def chat_with_ollama(messages: List[Dict[str, str]], model: Optional[str] = None,
                            temperature: float = 0.7, max_tokens: int = 1000) -> str:
    """Quick convenience function to chat with Ollama"""
    router = get_router()
    await router.init()
    
    llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in messages]
    response = await router.chat(llm_messages, model=model, temperature=temperature, max_tokens=max_tokens)
    
    return response.content if response.success else f"Error: {response.error}"


async def get_provider(name: str):
    """Get a specific provider instance"""
    router = get_router()
    await router.init()
    return router.get_provider(name)


# ─── EXPOSE KEY TYPES ──────────────────────────────────────────────

__all__ = [
    'LLMRouter',
    'LLMMessage',
    'LLMResponse',
    'OllamaProvider',
    'get_router',
    'reset_router',
    'chat_with_ollama',
    'get_provider'
]