import httpx
import json
from typing import Dict, List, Optional
from core.config import settings

class DocuChat:
    def __init__(self):
        self.model = settings.DOCUCHAT_MODEL
        self.enabled = settings.DOCUCHAT_ENABLED
    
    async def query_document(self, document_text: str, question: str) -> Dict:
        """Query a document using DocuChat"""
        if not self.enabled:
            return {"error": "DocuChat is disabled"}
        
        try:
            # Simulate DocuChat – replace with actual DocuChat API call
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/query",
                    json={
                        "document": document_text,
                        "question": question,
                        "model": self.model
                    }
                )
                data = response.json()
                return {
                    "answer": data.get("answer", ""),
                    "page_reference": data.get("page", "N/A"),
                    "confidence": data.get("confidence", 0.8)
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_contract(self, document_text: str) -> Dict:
        """Analyze a contract for key clauses"""
        if not self.enabled:
            return {"error": "DocuChat is disabled"}
        
        queries = [
            "What are the termination clauses?",
            "Identify all indemnity obligations",
            "What are the payment terms?",
            "Are there any non-compete clauses?",
            "What are the liability limits?",
            "Identify any force majeure clauses"
        ]
        
        results = {}
        for q in queries:
            result = await self.query_document(document_text, q)
            results[q] = result
        
        return results

docuchat = DocuChat()