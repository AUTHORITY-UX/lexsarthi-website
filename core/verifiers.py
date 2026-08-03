"""
core/verifiers.py
==================
15 legal verifiers — each checks a different dimension of LLM output.

Critical fix: every verifier checks for empty/null BEFORE calling .lower().
Previously a null Sarvam response crashed all 15 verifiers on .lower().
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    name: str
    passed: bool
    score: float  # 0.0 - 1.0
    notes: str = ""


def _safe_text(text) -> str:
    """Convert null/empty to safe empty string — the core fix."""
    if text is None:
        return ""
    return str(text)


class BaseVerifier:
    name: str = "base"

    def verify(self, query: str, response) -> VerificationResult:
        response = _safe_text(response)
        if not response.strip():
            return VerificationResult(self.name, False, 0.0, "skipped: empty response")
        return self._check(query, response)

    def _check(self, query: str, response: str) -> VerificationResult:
        raise NotImplementedError


class RelevanceVerifier(BaseVerifier):
    name = "relevance"
    def _check(self, q, r):
        qw, rw = set(q.lower().split()), set(r.lower().split())
        overlap = len(qw & rw) / max(len(qw), 1)
        return VerificationResult(self.name, overlap > 0.15, overlap, f"overlap: {overlap:.2%}")


class CoherenceVerifier(BaseVerifier):
    name = "coherence"
    def _check(self, q, r):
        sents = [s for s in r.split(".") if len(s.strip()) > 10]
        avg = sum(len(s.split()) for s in sents) / max(len(sents), 1)
        score = 1.0 if 5 <= avg <= 40 else 0.5
        return VerificationResult(self.name, score > 0.5, score, f"avg sentence: {avg:.0f}w")


class CitationVerifier(BaseVerifier):
    name = "citations"
    def _check(self, q, r):
        patterns = [r"Section\s+\d+", r"Sec\.\s*\d+", r"Art\.\s*\d+", r"v\.\s+[A-Z]",
                    r"AIR\s+\d{4}", r"\(\d{4}\)", r"Act,?\s+\d{4}", r"SCC", r"SC"]
        found = sum(1 for p in patterns if re.search(p, r))
        score = min(found / 3, 1.0)
        return VerificationResult(self.name, found > 0, score, f"citations: {found}")


class FactualConsistencyVerifier(BaseVerifier):
    name = "factual_consistency"
    def _check(self, q, r):
        hedging = ["might be", "could be", "possibly", "perhaps", "may be", "seems like", "likely"]
        hc = sum(1 for h in hedging if h in r.lower())
        score = 1.0 - min(hc / 5, 0.5)
        return VerificationResult(self.name, score > 0.5, score, f"hedge count: {hc}")


class CompletenessVerifier(BaseVerifier):
    name = "completeness"
    def _check(self, q, r):
        wc = len(r.split())
        score = 0.3 if wc < 50 else (0.6 if wc < 150 else 1.0)
        return VerificationResult(self.name, score > 0.5, score, f"words: {wc}")


class BiasVerifier(BaseVerifier):
    name = "bias"
    def _check(self, q, r):
        bias = ["obviously", "clearly", "undoubtedly", "must be"]
        bc = sum(1 for b in bias if b in r.lower())
        score = 1.0 - min(bc / 3, 1.0)
        return VerificationResult(self.name, score > 0.5, score, f"bias terms: {bc}")


class LegalAccuracyVerifier(BaseVerifier):
    name = "legal_accuracy"
    def _check(self, q, r):
        terms = ["statute", "precedent", "jurisdiction", "liability", "obligation",
                 "contract", "tort", "remedy", "court"]
        found = sum(1 for t in terms if t.lower() in r.lower())
        score = min(found / 3, 1.0)
        return VerificationResult(self.name, found >= 2, score, f"legal terms: {found}")


class ClarityVerifier(BaseVerifier):
    name = "clarity"
    def _check(self, q, r):
        awl = sum(len(w) for w in r.split()) / max(len(r.split()), 1)
        score = 1.0 if 4 <= awl <= 8 else 0.5
        return VerificationResult(self.name, score > 0.5, score, f"avg word len: {awl:.1f}")


class ToneVerifier(BaseVerifier):
    name = "tone"
    def _check(self, q, r):
        informal = ["yeah", "ok", "gonna", "wanna", "kinda", "lol", "btw"]
        found = sum(1 for i in informal if i in r.lower())
        score = 1.0 if found == 0 else 0.3
        return VerificationResult(self.name, score > 0.5, score, f"informal: {found}")


class StructureVerifier(BaseVerifier):
    name = "structure"
    def _check(self, q, r):
        structural = [r"^\d+\.", r"^-", r"^\*", r"^##", r"^###", r"\n\d+\."]
        found = sum(1 for p in structural if re.search(p, r, re.MULTILINE))
        score = min(found / 2, 1.0)
        return VerificationResult(self.name, found > 0, score, f"structure: {found}")


class SafetyVerifier(BaseVerifier):
    name = "safety"
    def _check(self, q, r):
        safety = ["consult", "legal advice", "professional", "attorney", "lawyer", "qualified", "disclaimer"]
        found = sum(1 for s in safety if s.lower() in r.lower())
        score = min(found / 2, 1.0)
        return VerificationResult(self.name, found > 0, score, f"safety: {found}")


class JurisdictionVerifier(BaseVerifier):
    name = "jurisdiction"
    def _check(self, q, r):
        terms = ["India", "Indian", "Supreme Court", "High Court", "Constitution", "IPC", "CrPC", "CPC", "BNSS", "BNS"]
        found = sum(1 for t in terms if t.lower() in r.lower())
        score = min(found / 2, 1.0)
        return VerificationResult(self.name, found > 0, score, f"jurisdiction: {found}")


class HallucinationVerifier(BaseVerifier):
    name = "hallucination"
    def _check(self, q, r):
        suspicious = re.findall(r"\b\d{4,}\b", r)
        score = 1.0 if len(suspicious) < 5 else 0.5
        return VerificationResult(self.name, score > 0.5, score, f"suspicious numbers: {len(suspicious)}")


class LanguageVerifier(BaseVerifier):
    name = "language"
    def _check(self, q, r):
        non_ascii = sum(1 for c in r if ord(c) > 127)
        score = 1.0 if non_ascii < len(r) * 0.1 else 0.5
        return VerificationResult(self.name, score > 0.5, score, f"non-ascii: {non_ascii}")


class ConfidenceVerifier(BaseVerifier):
    name = "confidence"
    def _check(self, q, r):
        confident = ["based on", "according to", "under", "pursuant to", "in accordance"]
        found = sum(1 for c in confident if c.lower() in r.lower())
        score = min(found / 2 + 0.3, 1.0)
        return VerificationResult(self.name, score > 0.5, score, f"confidence markers: {found}")


ALL_VERIFIERS: List[BaseVerifier] = [
    RelevanceVerifier(), CoherenceVerifier(), CitationVerifier(),
    FactualConsistencyVerifier(), CompletenessVerifier(), BiasVerifier(),
    LegalAccuracyVerifier(), ClarityVerifier(), ToneVerifier(),
    StructureVerifier(), SafetyVerifier(), JurisdictionVerifier(),
    HallucinationVerifier(), LanguageVerifier(), ConfidenceVerifier(),
]


def verify_all(query: str, response) -> List[VerificationResult]:
    return [v.verify(query, response) for v in ALL_VERIFIERS]


def verify_summary(query: str, response) -> dict:
    results = verify_all(query, response)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / max(len(results), 1)
    return {
        "total": len(results), "passed": passed, "failed": len(results) - passed,
        "avg_score": round(avg_score, 3),
        "verifiers": [{"name": r.name, "passed": r.passed, "score": r.score, "notes": r.notes} for r in results],
    }
