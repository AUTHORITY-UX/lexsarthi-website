"""
AI Judge - Final decision maker using Sarvam 105B.
The Judge reviews agent responses and verifier results to deliver the final verdict.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from unknown_verdict.config import settings
from sarvam.client import SarvamModel, sarvam_client, SarvamMessage
from .verifiers import VerificationResult, verifier_registry


class VerdictType(str, Enum):
    """Types of AI Judge verdicts."""
    APPROVED = "approved"
    APPROVED_WITH_NOTES = "approved_with_notes"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class JudgeVerdict:
    """A verdict from the AI Judge."""
    verdict_id: str
    verdict_type: VerdictType
    score: float  # 0.0 to 1.0
    reasoning: str
    recommendations: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    verification_summary: Optional[dict] = None
    judge_model: str = settings.SARVAM_105B_MODEL
    judge_reasoning: str = ""  # Sarvam 105B's detailed reasoning
    timestamp: str = ""
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "verdict_id": self.verdict_id,
            "verdict_type": self.verdict_type.value,
            "score": round(self.score, 4),
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
            "issues": self.issues,
            "verification_summary": self.verification_summary,
            "judge_model": self.judge_model,
            "judge_reasoning": self.judge_reasoning,
            "timestamp": self.timestamp,
            "latency_ms": round(self.latency_ms, 2),
        }


# Judge system prompt
JUDGE_SYSTEM_PROMPT = """You are the AI Judge of Unknown Verdict, the supreme legal AI arbiter.

Your role:
1. Review the legal response provided by a specialist agent.
2. Evaluate it against the verification results.
3. Deliver a final verdict on whether the response is legally sound.

You must:
- Be impartial and rigorous in your analysis.
- Identify any legal errors, missing citations, or logical fallacies.
- Provide a clear verdict: APPROVED, APPROVED_WITH_NOTES, NEEDS_REVISION, or REJECTED.
- Score the response from 0.0 to 1.0 based on legal accuracy and completeness.
- Recommend specific improvements if needed.

Your analysis should reference:
- Applicable statutes and case law
- Procedural requirements
- Jurisdictional considerations
- Ethical obligations

Format your verdict as structured legal reasoning."""

# Counter for verdict IDs
_verdict_counter = 0


def _next_verdict_id() -> str:
    global _verdict_counter
    _verdict_counter += 1
    return f"VRD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{_verdict_counter:04d}"


class AIJudge:
    """
    The AI Judge uses Sarvam 105B to make final decisions on all legal queries.
    It reviews agent responses, verification results, and delivers a verdict.
    """

    def __init__(self) -> None:
        self.model = settings.SARVAM_105B_MODEL
        self.version = "40.0"
        self.total_verdicts: int = 0
        self.approved: int = 0
        self.rejected: int = 0
        self.escalated: int = 0
        self.avg_score: float = 0.0
        self.avg_latency_ms: float = 0.0

    async def evaluate(
        self,
        query: str,
        agent_response: str,
        agent_name: str,
        agent_specialization: str,
        verification_results: List[VerificationResult],
        context: Optional[dict] = None,
    ) -> JudgeVerdict:
        """Evaluate an agent's response and deliver a verdict."""
        start = time.time()
        self.total_verdicts += 1

        # Get verification summary
        verification_summary = verifier_registry.get_verification_summary(verification_results)
        overall_score = verification_summary["overall_score"]

        # Build the judge prompt
        verification_details = "\n".join(
            f"  - {r.verifier_name} ({r.verifier_type.value}): {'PASS' if r.passed else 'FAIL'} "
            f"score={r.score:.2f} {'— ' + r.details if r.details else ''}"
            + (f" issues: {'; '.join(r.issues)}" if r.issues else "")
            for r in verification_results
        )

        judge_prompt = f"""LEGAL QUERY:
{query}

AGENT: {agent_name} (Specialization: {agent_specialization})

AGENT RESPONSE:
{agent_response}

VERIFICATION RESULTS:
{verification_summary['verifiers_passed']}/{verification_summary['verifiers_total']} verifiers passed.
Overall verification score: {verification_summary['overall_score']:.2%}
Issues found: {verification_summary['issue_count']}

Detailed verifier results:
{verification_details}

As the AI Judge, analyze the agent's response for legal accuracy, completeness, and soundness.
Provide:
1. Your assessment of the response's legal soundness.
2. Any errors or omissions you identify.
3. Your verdict (APPROVED / APPROVED_WITH_NOTES / NEEDS_REVISION / REJECTED).
4. A score from 0.0 to 1.0.
5. Specific recommendations for improvement.
"""

        judge_reasoning = ""
        # Try to get Sarvam 105B's analysis
        if sarvam_client.is_configured:
            try:
                response = await sarvam_client.reason(
                    prompt=judge_prompt,
                    system_prompt=JUDGE_SYSTEM_PROMPT,
                    temperature=0.2,
                    max_tokens=4096,
                )
                if response.success:
                    judge_reasoning = response.content
                    # Parse verdict from response (simplified)
                    content_lower = response.content.lower()
                    if "approved_with_notes" in content_lower or "approved with notes" in content_lower:
                        verdict_type = VerdictType.APPROVED_WITH_NOTES
                    elif "needs_revision" in content_lower or "needs revision" in content_lower:
                        verdict_type = VerdictType.NEEDS_REVISION
                    elif "rejected" in content_lower:
                        verdict_type = VerdictType.REJECTED
                    elif "approved" in content_lower:
                        verdict_type = VerdictType.APPROVED
                    else:
                        # Fall back to verification-based verdict
                        if overall_score >= 0.85:
                            verdict_type = VerdictType.APPROVED
                        elif overall_score >= 0.7:
                            verdict_type = VerdictType.APPROVED_WITH_NOTES
                        elif overall_score >= 0.5:
                            verdict_type = VerdictType.NEEDS_REVISION
                        else:
                            verdict_type = VerdictType.REJECTED
                else:
                    verdict_type = self._verdict_from_score(overall_score)
                    judge_reasoning = f"Sarvam 105B unavailable: {response.error}. Verdict based on verification scores."
            except Exception as e:
                verdict_type = self._verdict_from_score(overall_score)
                judge_reasoning = f"Judge LLM error: {e}. Verdict based on verification scores."
        else:
            # Sarvam not configured - use verification-based scoring
            verdict_type = self._verdict_from_score(overall_score)
            judge_reasoning = (
                "Sarvam 105B not configured. Verdict determined by automated verification system. "
                f"Verification score: {overall_score:.2%}. "
                f"Pass rate: {verification_summary['pass_rate']:.1f}%."
            )

        latency = (time.time() - start) * 1000

        # Update stats
        self.avg_latency_ms = ((self.avg_latency_ms * (self.total_verdicts - 1)) + latency) / self.total_verdicts
        self.avg_score = ((self.avg_score * (self.total_verdicts - 1)) + overall_score) / self.total_verdicts
        if verdict_type in (VerdictType.APPROVED, VerdictType.APPROVED_WITH_NOTES):
            self.approved += 1
        elif verdict_type == VerdictType.REJECTED:
            self.rejected += 1

        # Build reasoning
        reasoning = self._build_reasoning(
            verdict_type, overall_score, verification_summary, judge_reasoning
        )

        recommendations = self._build_recommendations(verification_results, verdict_type)

        return JudgeVerdict(
            verdict_id=_next_verdict_id(),
            verdict_type=verdict_type,
            score=overall_score,
            reasoning=reasoning,
            recommendations=recommendations,
            issues=verification_summary.get("issues_found", []),
            verification_summary=verification_summary,
            judge_reasoning=judge_reasoning,
            latency_ms=latency,
        )

    def _verdict_from_score(self, score: float) -> VerdictType:
        if score >= 0.85:
            return VerdictType.APPROVED
        elif score >= 0.7:
            return VerdictType.APPROVED_WITH_NOTES
        elif score >= 0.5:
            return VerdictType.NEEDS_REVISION
        else:
            return VerdictType.REJECTED

    def _build_reasoning(
        self, verdict_type: VerdictType, score: float,
        verification_summary: dict, judge_reasoning: str
    ) -> str:
        base = (
            f"The AI Judge has reviewed the response and verdict is: {verdict_type.value.upper()}. "
            f"Overall verification score: {score:.2%}. "
            f"{verification_summary['verifiers_passed']}/{verification_summary['verifiers_total']} "
            f"verifiers passed ({verification_summary['pass_rate']:.1f}% pass rate). "
        )
        if judge_reasoning:
            base += f"\n\nJudge Analysis:\n{judge_reasoning}"
        return base

    def _build_recommendations(self, results: List[VerificationResult], verdict_type: VerdictType) -> List[str]:
        recs: List[str] = []
        for r in results:
            if not r.passed:
                for issue in r.issues:
                    recs.append(f"[{r.verifier_name}] {issue}")
        if verdict_type == VerdictType.APPROVED:
            recs.insert(0, "Response meets quality standards. No changes required.")
        elif verdict_type == VerdictType.APPROVED_WITH_NOTES:
            recs.insert(0, "Response is acceptable but has minor issues to address.")
        elif verdict_type == VerdictType.NEEDS_REVISION:
            recs.insert(0, "Response requires revision before final delivery.")
        elif verdict_type == VerdictType.REJECTED:
            recs.insert(0, "Response does not meet legal quality standards. Regenerate.")
        return recs

    def stats(self) -> dict:
        return {
            "version": self.version,
            "model": self.model,
            "total_verdicts": self.total_verdicts,
            "approved": self.approved,
            "rejected": self.rejected,
            "escalated": self.escalated,
            "approval_rate": round(self.approved / self.total_verdicts * 100, 1) if self.total_verdicts else 0.0,
            "avg_score": round(self.avg_score, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "status": "operational",
        }

    def to_dict(self) -> dict:
        return {
            "name": "AI Judge",
            "version": self.version,
            "model": self.model,
            "role": "Final decision maker",
            "status": "operational",
            "stats": self.stats(),
        }


# Singleton
ai_judge = AIJudge()
