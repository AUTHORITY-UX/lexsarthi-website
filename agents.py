# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

import json
from schemas import LegalAgentOutput, Citation, AgentStatus
from openrouter_client import call_openrouter

class ContractReviewAgent:
    SYSTEM_PROMPT = """
You are Lexsarthi's Contract Review Agent. Analyze the contract text.
Extract critical clauses, risks, missing terms, and compliance flags.
OUTPUT MUST BE VALID JSON matching this schema:
{
    "status": "success" or "partial" or "error",
    "summary": "executive summary (max 300 chars)",
    "key_findings": ["finding 1", "finding 2"],
    "citations": [{"source": "Section X", "excerpt": "quoted text"}],
    "confidence_score": 0.85,
    "suggested_next_steps": ["step 1"],
    "agent_type": "contract_review"
}
Every claim needs a citation. Never fabricate citations.
If uncertain, set confidence < 0.5 and status to 'partial'.
"""

    def run(self, document_text: str) -> LegalAgentOutput:
        try:
            raw = call_openrouter(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=f"Contract text:\n\n{document_text[:8000]}",
                response_format="json_object"
            )
            data = json.loads(raw)
            return LegalAgentOutput(**data)
        except Exception as e:
            return LegalAgentOutput(
                status=AgentStatus.ERROR,
                summary="Agent failed to process document.",
                key_findings=[],
                citations=[],
                confidence_score=0.0,
                suggested_next_steps=["Try a shorter document", "Contact support"],
                agent_type="contract_review",
                error_message=str(e)
            )

# Add other agents here (DueDiligence, Research, etc.)
def get_agent(agent_type: str):
    if agent_type == "contract_review":
        return ContractReviewAgent()
    # elif agent_type == "due_diligence": return DueDiligenceAgent()
    raise ValueError(f"Unknown agent type: {agent_type}")