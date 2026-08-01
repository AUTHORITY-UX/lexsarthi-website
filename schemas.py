"""
Pydantic schemas/models for API request/response validation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ===== Chat Endpoints =====

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for /api/chat"""
    message: str = Field(..., min_length=1, description="User's legal query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    specialization: Optional[str] = Field(None, description="Preferred legal specialization")
    use_rag: bool = Field(True, description="Use RAG retrieval for context")
    model: Optional[str] = Field(None, description="Override model: sarvam-105b or sarvam-30b")
    history: List[ChatMessage] = Field(default_factory=list, description="Conversation history")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="File attachments metadata")


class ChatResponse(BaseModel):
    """Response from /api/chat"""
    response: str
    agent_id: str
    agent_name: str
    specialization: str
    model: str
    rag_context_used: bool = False
    rag_sources: List[Dict[str, Any]] = Field(default_factory=list)
    verification: Optional[Dict[str, Any]] = None
    verdict: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    conversation_id: str = ""
    timestamp: str = ""


# ===== Sarvam Endpoints =====

class SarvamReasonRequest(BaseModel):
    """Request for /api/sarvam/reason"""
    query: str = Field(..., min_length=1, description="Legal reasoning query")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(8192, ge=1, le=32768)
    use_rag: bool = Field(True, description="Augment with RAG context")


class SarvamReasonResponse(BaseModel):
    """Response from /api/sarvam/reason"""
    reasoning: str
    model: str
    rag_context_used: bool = False
    rag_sources: List[Dict[str, Any]] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=dict)
    latency_ms: float = 0.0


class SarvamStatusResponse(BaseModel):
    """Response from /api/sarvam/status"""
    status: str
    configured: bool
    message: str
    base_url: str = ""
    models: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)


# ===== Agent Endpoints =====

class AgentStatusResponse(BaseModel):
    """Response from /api/agents/status"""
    total_agents: int
    online: int
    offline: int
    elite_agents: int
    by_specialization: Dict[str, int]
    tiers: Dict[str, int]
    agents: List[Dict[str, Any]] = Field(default_factory=list)


# ===== Compliance Endpoints =====

class ComplianceSnapshotResponse(BaseModel):
    """Response from /api/compliance/snapshot"""
    overall_score: float
    frameworks: Dict[str, Dict[str, Any]]
    last_updated: str
    status: str


# ===== Market/Trading Endpoints =====

class MarketDataResponse(BaseModel):
    """Response from /api/market/global"""
    status: str
    timestamp: str
    indices: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    commodities: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    currencies: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class TradingIndicesResponse(BaseModel):
    """Response from /api/trading/indices"""
    status: str
    timestamp: str
    indices: Dict[str, Dict[str, Any]]


# ===== Sports Endpoints =====

class CricketScoreResponse(BaseModel):
    """Response from /api/sports/cricket"""
    status: str
    timestamp: str
    matches: List[Dict[str, Any]]


# ===== News Endpoints =====

class LegalNewsResponse(BaseModel):
    """Response from /api/news/real"""
    status: str
    timestamp: str
    articles: List[Dict[str, Any]]
    source_count: int


# ===== Lens Endpoints =====

class LensRequest(BaseModel):
    """Request for /api/lens/agents"""
    url: str = Field(..., description="Website URL to scan")
    depth: str = Field("standard", description="Scan depth: quick, standard, deep")
    frameworks: List[str] = Field(
        default_factory=lambda: ["GDPR", "DPDPA", "CCPA"],
        description="Compliance frameworks to check"
    )


class LensResponse(BaseModel):
    """Response from /api/lens/agents"""
    url: str
    status: str
    timestamp: str
    compliance_scores: Dict[str, float]
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    scan_depth: str


# ===== Payment Endpoints =====

class PaymentKeyResponse(BaseModel):
    """Response from /api/payment/key"""
    key_id: str
    amount: int
    currency: str = "INR"
    amount_display: str
    description: str
    configured: bool


# ===== DSAR Endpoints =====

class DSARRequest(BaseModel):
    """Request for /api/privacy/dsar"""
    request_type: str = Field(..., description="Type: access, correction, erasure, portability, objection")
    data_subject_name: str = Field(..., min_length=1)
    data_subject_email: str = Field(..., min_length=3)
    request_details: str = Field("", description="Additional details")
    identification_verified: bool = Field(False, description="Whether identity is verified")
    frameworks: List[str] = Field(
        default_factory=lambda: ["DPDP", "GDPR"],
        description="Applicable frameworks"
    )

    @field_validator("request_type")
    @classmethod
    def validate_request_type(cls, v: str) -> str:
        allowed = ["access", "correction", "erasure", "portability", "objection"]
        v_lower = v.lower().strip()
        if v_lower not in allowed:
            raise ValueError(f"request_type must be one of: {', '.join(allowed)}")
        return v_lower


class DSARResponse(BaseModel):
    """Response from /api/privacy/dsar"""
    request_id: str
    status: str
    request_type: str
    frameworks: List[str]
    estimated_completion_days: int
    rights_exercised: List[str]
    next_steps: List[str]
    timestamp: str


# ===== Generic Responses =====

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    uptime_seconds: float
    components: Dict[str, str]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
