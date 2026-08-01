# ============================================
# SARVAM_INTEGRATION.PY - FIXED VERSION
# ============================================

import os
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger("unknown_verdict.sarvam")

# ============================================
# CONFIGURATION
# ============================================

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE_URL = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai/v1")

# ============================================
# SARVAM ENGINE - USING DIRECT API
# ============================================

class SarvamEngine:
    """Sarvam AI integration for Unknown Verdict - Direct API approach"""
    
    def __init__(self):
        self.api_key = SARVAM_API_KEY
        self.base_url = SARVAM_BASE_URL
        
        if self.api_key:
            logger.info("✅ Sarvam AI initialized with API key")
        else:
            logger.warning("⚠️ Sarvam API key not set - using mock mode")
    
    async def chat(self, messages: List[Dict], model: str = "sarvam-30b", temperature: float = 0.7) -> str:
        """Send a chat request to Sarvam"""
        if not self.api_key:
            return self._mock_response(messages)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 4096
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    logger.error(f"Sarvam API error: {response.status_code} - {response.text}")
                    return f"Error: {response.status_code} - {response.text}"
                    
        except Exception as e:
            logger.error(f"Sarvam chat error: {e}")
            return f"Error: {str(e)}"
    
    async def chat_with_reasoning(self, query: str, context: Dict, reasoning_effort: str = "medium") -> str:
        """Chat with reasoning mode for complex legal analysis"""
        messages = [
            {"role": "system", "content": "You are AI Judge v40.0, a legal AI assistant. Provide detailed legal reasoning with citations."},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
        ]
        
        # Use 105B model for reasoning tasks
        return await self.chat(messages, model="sarvam-105b", temperature=0.3)
    
    async def analyze_document(self, text: str, language: str = "en-IN") -> Dict:
        """Analyze a legal document using Sarvam"""
        messages = [
            {"role": "system", "content": "You are a legal document analyst. Extract key clauses, risks, and compliance issues."},
            {"role": "user", "content": f"Analyze this legal document in {language}:\n\n{text[:5000]}"}
        ]
        
        response = await self.chat(messages, model="sarvam-105b", temperature=0.2)
        
        return {
            "analysis": response,
            "language": language,
            "model": "sarvam-105b"
        }
    
    def _mock_response(self, messages: List[Dict]) -> str:
        """Mock response when API key is missing"""
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"""[Sarvam Mock Mode] 
        
Question: {last_user_msg[:150]}...

Response: This is a simulated Sarvam response. To use the real Sarvam AI:
1. Get an API key from Sarvam AI
2. Set SARVAM_API_KEY environment variable
3. The system will automatically use Sarvam models

Sarvam AI features:
- 105B parameter model for complex reasoning
- Support for 22 Indian languages
- Voice-first architecture
- Sovereign AI infrastructure

Please set SARVAM_API_KEY to enable real Sarvam responses."""


# ============================================
# SINGLETON INSTANCE
# ============================================

_sarvam_instance = None

def get_sarvam() -> SarvamEngine:
    global _sarvam_instance
    if _sarvam_instance is None:
        _sarvam_instance = SarvamEngine()
    return _sarvam_instance