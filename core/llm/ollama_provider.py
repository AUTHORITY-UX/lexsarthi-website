# core/llm/ollama_provider.py

import httpx
import json
import time
import logging
from typing import List, Optional, AsyncGenerator

from core.config import settings

logger = logging.getLogger(__name__)


class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class LLMResponse:
    def __init__(self, content: str, provider: str, model: str, 
                 latency_ms: float = 0, success: bool = True, 
                 error: Optional[str] = None):
        self.content = content
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms
        self.success = success
        self.error = error


class OllamaProvider:
    """Ollama LLM provider – local, free, offline-first"""
    
    def __init__(self, model: str = None):
        self.model = model or settings.OLLAMA_MODEL
        self.base_url = settings.OLLAMA_HOST
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client
    
    async def chat(self, messages: List[LLMMessage], 
                   temperature: float = 0.7, 
                   max_tokens: int = 1000, 
                   **kwargs) -> LLMResponse:
        """Send a chat request to Ollama"""
        start_time = time.time()
        
        try:
            client = await self._get_client()
            
            # Convert messages to dict format
            messages_dict = [{"role": m.role, "content": m.content} for m in messages]
            
            # Prepare request
            request_data = {
                "model": self.model,
                "messages": messages_dict,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": kwargs.get("top_p", 0.9)
                }
            }
            
            # Make request
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=request_data
            )
            response.raise_for_status()
            
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract content
            content = data.get("message", {}).get("content", "")
            if not content:
                content = "No content in response"
            
            return LLMResponse(
                content=content,
                provider="ollama",
                model=self.model,
                latency_ms=latency_ms,
                success=True
            )
            
        except httpx.ConnectError:
            return LLMResponse(
                content="Ollama server is not running. Please start Ollama first.",
                provider="ollama",
                model=self.model,
                latency_ms=0,
                success=False,
                error="Connection refused"
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                provider="ollama",
                model=self.model,
                latency_ms=0,
                success=False,
                error=str(e)
            )
    
    async def stream(self, messages: List[LLMMessage],
                     temperature: float = 0.7,
                     max_tokens: int = 1000,
                     **kwargs) -> AsyncGenerator[str, None]:
        """Stream responses from Ollama"""
        try:
            client = await self._get_client()
            
            messages_dict = [{"role": m.role, "content": m.content} for m in messages]
            
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages_dict,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None