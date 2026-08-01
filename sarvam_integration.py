# ============================================
# SARVAM_INTEGRATION.PY
# Sarvam AI + Unknown Verdict Integration
# ============================================

import os
import logging
from typing import Dict, List, Optional
from langchain_sarvam import ChatSarvam
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("unknown_verdict.sarvam")

# ============================================
# CONFIGURATION
# ============================================

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_DEFAULT_MODEL = os.getenv("SARVAM_DEFAULT_MODEL", "sarvam-105b")
SARVAM_FAST_MODEL = os.getenv("SARVAM_FAST_MODEL", "sarvam-30b")

# ============================================
# SARVAM ENGINE
# ============================================

class SarvamEngine:
    """Sarvam AI integration for Unknown Verdict"""
    
    def __init__(self):
        self.api_key = SARVAM_API_KEY
        self.default_model = SARVAM_DEFAULT_MODEL
        self.fast_model = SARVAM_FAST_MODEL
        
        if self.api_key:
            logger.info("✅ Sarvam AI initialized with API key")
        else:
            logger.warning("⚠️ Sarvam API key not set")
    
    def get_chat_model(self, model: Optional[str] = None, temperature: float = 0.7, reasoning: Optional[str] = None):
        """Get a Sarvam chat model instance"""
        model_name = model or self.default_model
        
        kwargs = {
            "model": model_name,
            "temperature": temperature,
            "sarvam_api_key": self.api_key,
        }
        
        # Add reasoning effort for 105B model
        if model_name == "sarvam-105b" and reasoning:
            kwargs["reasoning_effort"] = reasoning  # "low", "medium", "high"
        
        return ChatSarvam(**kwargs)
    
    async def chat(self, messages: List[Dict], model: Optional[str] = None, temperature: float = 0.7) -> str:
        """Send a chat request to Sarvam"""
        if not self.api_key:
            logger.warning("⚠️ Sarvam API key missing, falling back to mock")
            return self._mock_response(messages)
        
        try:
            llm = self.get_chat_model(model, temperature)
            
            # Convert messages
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                else:
                    langchain_messages.append(HumanMessage(content=msg["content"]))
            
            response = llm.invoke(langchain_messages)
            return response.content
            
        except Exception as e:
            logger.error(f"❌ Sarvam chat error: {e}")
            return f"Error: {str(e)}"
    
    async def chat_with_reasoning(self, query: str, context: Dict, reasoning_effort: str = "medium") -> str:
        """Chat with reasoning mode for complex legal analysis"""
        messages = [
            {"role": "system", "content": "You are a legal AI assistant. Analyze the query and provide a reasoned legal response with citations."},
            {"role": "user", "content": f"Context: {context}\n\nQuery: {query}"}
        ]
        
        llm = self.get_chat_model("sarvam-105b", reasoning=reasoning_effort)
        
        langchain_messages = [
            SystemMessage(content="You are a legal AI assistant. Provide detailed legal reasoning."),
            HumanMessage(content=f"Context: {context}\n\nQuery: {query}")
        ]
        
        response = llm.invoke(langchain_messages)
        return response.content
    
    async def analyze_document(self, text: str, language: str = "en-IN") -> Dict:
        """Analyze a legal document using Sarvam"""
        messages = [
            {"role": "system", "content": "You are a legal document analyst. Extract key clauses, risks, and compliance issues."},
            {"role": "user", "content": f"Analyze this legal document in {language}:\n\n{text}"}
        ]
        
        response = await self.chat(messages, model="sarvam-105b")
        
        return {
            "analysis": response,
            "language": language,
            "model": "sarvam-105b"
        }
    
    async def generate_legal_report(self, case_data: Dict) -> str:
        """Generate a legal report using Sarvam"""
        messages = [
            {"role": "system", "content": "You are a legal analyst. Generate a structured legal report."},
            {"role": "user", "content": f"Generate a legal report based on:\n{case_data}"}
        ]
        
        return await self.chat(messages, model="sarvam-105b", temperature=0.3)
    
    def _mock_response(self, messages: List[Dict]) -> str:
        """Mock response when API key is missing"""
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[Sarvam Mock] I would respond to: '{last_user_msg[:100]}...'\n\nPlease set SARVAM_API_KEY environment variable to use actual Sarvam models."


# ============================================
# SINGLETON INSTANCE
# ============================================

_sarvam_instance = None

def get_sarvam() -> SarvamEngine:
    global _sarvam_instance
    if _sarvam_instance is None:
        _sarvam_instance = SarvamEngine()
    return _sarvam_instance