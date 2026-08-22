import httpx
import time
from typing import List, Optional
from core.config import settings

class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class LLMResponse:
    def __init__(self, content: str, provider: str, model: str, latency_ms: float = 0, success: bool = True, error: Optional[str] = None):
        self.content = content
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms
        self.success = success
        self.error = error

class OllamaProvider:
    def __init__(self, model: str = None):
        self.model = model or settings.OLLAMA_MODEL
        self.base_url = settings.OLLAMA_HOST
    
    async def chat(self, messages: List[LLMMessage], temperature: float = 0.7, max_tokens: int = 1000, **kwargs) -> LLMResponse:
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    }
                )
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                return LLMResponse(
                    content=data["message"]["content"],
                    provider="ollama",
                    model=self.model,
                    latency_ms=latency_ms,
                    success=True
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

    async def stream(self, messages: List[LLMMessage], **kwargs):
        """Stream responses from Ollama"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                        "stream": True,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.7),
                            "num_predict": kwargs.get("max_tokens", 1000)
                        }
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            import json
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
        except Exception as e:
            yield f"Error: {str(e)}"