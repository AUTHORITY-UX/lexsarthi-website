# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator
from enum import Enum

class AgentStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"

class Citation(BaseModel):
    source: str = Field(..., description="Document section or case law")
    excerpt: str = Field(..., description="Quoted text")
    page_or_section: Optional[str] = None
    url: Optional[str] = None

class LegalAgentOutput(BaseModel):
    status: AgentStatus
    summary: str = Field(..., max_length=300)
    key_findings: List[str]
    citations: List[Citation]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    suggested_next_steps: List[str] = Field(default_factory=list)
    agent_type: Literal["contract_review", "due_diligence", "legal_research", "compliance", "general"]
    raw_response: Optional[str] = None
    error_message: Optional[str] = None

    @model_validator(mode='after')
    def check_citations(self):
        if self.status == AgentStatus.SUCCESS and len(self.citations) == 0:
            raise ValueError("SUCCESS status requires at least 1 citation.")
        if self.confidence_score < 0.3 and self.status == AgentStatus.SUCCESS:
            raise ValueError("Confidence < 0.3 but status is SUCCESS.")
        return self