import httpx
from typing import List, Dict, Optional
from core.config import settings

class LQAI:
    def __init__(self):
        self.enabled = settings.LQAI_ENABLED
        self.host = settings.LQAI_HOST
    
    async def verify_citations(self, text: str, citations: List[str]) -> Dict:
        """Verify citations using LQ.AI's citation engine"""
        if not self.enabled:
            return {"error": "LQ.AI is disabled"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.host}/api/verify",
                    json={
                        "text": text,
                        "citations": citations
                    }
                )
                data = response.json()
                return {
                    "verified_citations": data.get("verified", []),
                    "unverified_citations": data.get("unverified", []),
                    "all_verified": data.get("all_verified", False)
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_citations(self, text: str) -> Dict:
        """Generate citations for legal text"""
        if not self.enabled:
            return {"error": "LQ.AI is disabled"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "text": text
                    }
                )
                data = response.json()
                return {
                    "citations": data.get("citations", []),
                    "confidence": data.get("confidence", 0.0)
                }
        except Exception as e:
            return {"error": str(e)}

lqai = LQAI()