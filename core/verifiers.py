"""
Verification System - 15 quality-check verifiers.
Each verifier checks a different aspect of agent responses before the AI Judge rules.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from unknown_verdict.config import settings


class VerifierType(str, Enum):
    """Types of quality verification."""
    ACCURACY = "accuracy"
    CITATION = "citation"
    REASONING = "reasoning"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    JURISDICTION = "jurisdiction"
    STATUTORY = "statutory"
    ETHICS = "ethics"
    BIAS = "bias"
    LANGUAGE = "language"
    HALLUCINATION = "hallucination"
    PRECEDENT = "precedent"
    LOGICAL_FLOW = "logical_flow"
    FACTUAL = "factual"
    COMPLIANCE = "compliance"


@dataclass
class VerificationResult:
    """Result of a single verification check."""
    verifier_id: str
    verifier_name: str
    verifier_type: VerifierType
    passed: bool
    score: float  # 0.0 to 1.0
    details: str = ""
    issues: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "verifier_id": self.verifier_id,
            "verifier_name": self.verifier_name,
            "verifier_type": self.verifier_type.value,
            "passed": self.passed,
            "score": round(self.score, 4),
            "details": self.details,
            "issues": self.issues,
            "timestamp": self.timestamp,
        }


@dataclass
class Verifier:
    """A quality-check verifier."""
    verifier_id: str
    name: str
    verifier_type: VerifierType
    description: str
    weight: float = 1.0  # relative importance
    min_score: float = 0.75
    checks_run: int = 0
    checks_passed: int = 0
    avg_score: float = 0.0
    enabled: bool = True

    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        """Run verification on a response. Override in subclasses."""
        raise NotImplementedError

    def _base_result(self, passed: bool, score: float, details: str, issues: List[str]) -> VerificationResult:
        self.checks_run += 1
        if passed:
            self.checks_passed += 1
        n = self.checks_run
        self.avg_score = ((self.avg_score * (n - 1)) + score) / n
        return VerificationResult(
            verifier_id=self.verifier_id,
            verifier_name=self.name,
            verifier_type=self.verifier_type,
            passed=passed,
            score=score,
            details=details,
            issues=issues,
        )

    def to_dict(self) -> dict:
        pass_rate = (self.checks_passed / self.checks_run * 100) if self.checks_run > 0 else 0.0
        return {
            "verifier_id": self.verifier_id,
            "name": self.name,
            "type": self.verifier_type.value,
            "description": self.description,
            "weight": self.weight,
            "min_score": self.min_score,
            "enabled": self.enabled,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "pass_rate": round(pass_rate, 1),
            "avg_score": round(self.avg_score, 4),
        }


class AccuracyVerifier(Verifier):
    """Verifies factual accuracy of legal claims."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        score = 1.0
        # Check for hedging language that might indicate uncertainty
        hedging = ["might be", "could possibly", "perhaps", "maybe", "I think"]
        hedge_count = sum(1 for h in hedging if h.lower() in response.lower())
        if hedge_count > 3:
            score -= 0.15
            issues.append("Excessive hedging language detected")

        # Check for definitive claims without citation
        definitive_patterns = [
            r"according to (?:Section|Article|Rule) \d+",
            r"under (?:Section|Article|Rule) \d+",
            r"as per (?:Section|Article|Rule) \d+",
        ]
        has_citation = any(re.search(p, response, re.IGNORECASE) for p in definitive_patterns)

        if len(response) > 200 and not has_citation:
            score -= 0.2
            issues.append("Long response without specific statutory citation")

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Accuracy check: {'passed' if passed else 'needs review'}",
            issues=issues,
        )


class CitationVerifier(Verifier):
    """Verifies presence and format of legal citations."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        citations_found = 0

        # Count citation patterns
        citation_patterns = [
            r"(?:Section|Sec\.?)\s+\d+",
            r"(?:Article|Art\.?)\s+\d+",
            r"(?:Rule|R\.)\s+\d+",
            r"\d+\s+(?:SCC|AIR|SC|LLJ)\s+\d+",
            r"(?:v\.|vs\.|versus)\s+",
            r"(?:Act|Act,?)\s+\d{4}",
        ]
        for pattern in citation_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            citations_found += len(matches)

        if citations_found == 0 and len(response) > 100:
            score = 0.4
            issues.append("No legal citations found in response")
        elif citations_found == 1:
            score = 0.7
        elif citations_found >= 2:
            score = 1.0
        else:
            score = 0.8

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Citation check: {citations_found} citations found",
            issues=issues,
        )


class ReasoningVerifier(Verifier):
    """Verifies logical reasoning structure."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        reasoning_markers = [
            "therefore", "because", "since", "as a result", "consequently",
            "however", "nevertheless", "furthermore", "in addition",
            "on the other hand", "thus", "hence", "accordingly",
        ]
        marker_count = sum(1 for m in reasoning_markers if m.lower() in response.lower())

        # Check for structured analysis (lists, steps)
        has_structure = bool(re.search(r"(?:\d+\.|\-|\*)\s", response))

        score = min(1.0, 0.3 + (marker_count * 0.15) + (0.2 if has_structure else 0))
        if marker_count == 0:
            issues.append("No reasoning markers found")
        if not has_structure:
            issues.append("Response lacks structured formatting")

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Reasoning check: {marker_count} reasoning markers, structured={has_structure}",
            issues=issues,
        )


class CompletenessVerifier(Verifier):
    """Verifies response completeness."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        word_count = len(response.split())

        if word_count < 50:
            score = 0.3
            issues.append(f"Response too short ({word_count} words)")
        elif word_count < 150:
            score = 0.6
            issues.append("Response could be more comprehensive")
        elif word_count > 2000:
            score = 0.85
            issues.append("Response very long - consider summarizing")
        else:
            score = 1.0

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Completeness check: {word_count} words",
            issues=issues,
        )


class ConsistencyVerifier(Verifier):
    """Verifies internal consistency of the response."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        sentences = response.split(". ")
        if len(sentences) < 2:
            score = 0.8
            return self._base_result(passed=True, score=score,
                                     details="Insufficient text for consistency check", issues=issues)

        # Check for contradictions (simplified)
        negation_pairs = [("must", "must not"), ("shall", "shall not"),
                          ("is legal", "is illegal"), ("is valid", "is invalid")]
        contradictions = 0
        lower_resp = response.lower()
        for pos, neg in negation_pairs:
            if pos in lower_resp and neg in lower_resp:
                contradictions += 1
                issues.append(f"Potential contradiction: '{pos}' vs '{neg}'")

        score = max(0.0, 1.0 - (contradictions * 0.3))
        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Consistency check: {contradictions} potential contradictions",
            issues=issues,
        )


class JurisdictionVerifier(Verifier):
    """Verifies jurisdiction is appropriate."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        jurisdiction_markers = ["India", "Indian", "Supreme Court", "High Court",
                                "IPC", "CrPC", "Constitution", "RERA", "DPDP"]

        jurisdiction_count = sum(1 for m in jurisdiction_markers if m.lower() in response.lower())
        if jurisdiction_count == 0:
            score = 0.5
            issues.append("No jurisdiction markers found")
        else:
            score = min(1.0, 0.5 + (jurisdiction_count * 0.15))

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Jurisdiction check: {jurisdiction_count} markers found",
            issues=issues,
        )


class StatutoryVerifier(Verifier):
    """Verifies statutory references are present and formatted."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        statutory_patterns = [
            r"(?:Act|Ordinance|Code)\s*,?\s*\d{4}",
            r"(?:Section|Sec\.?|§)\s+\d+[A-Z]?",
            r"(?:Article|Art\.?)\s+\d+[A-Z]?",
            r"(?:Schedule|Sched\.?)\s+[IVXLCDM]+",
        ]
        refs_found = sum(len(re.findall(p, response, re.IGNORECASE)) for p in statutory_patterns)

        if refs_found >= 2:
            score = 1.0
        elif refs_found == 1:
            score = 0.7
        else:
            score = 0.3
            issues.append("No statutory references found")

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Statutory check: {refs_found} references found",
            issues=issues,
        )


class EthicsVerifier(Verifier):
    """Verifies ethical considerations are addressed."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        # Check for disclaimer
        has_disclaimer = any(d in response.lower() for d in [
            "disclaimer", "not legal advice", "consult", "professional",
            "qualified lawyer", "attorney"
        ])
        if not has_disclaimer and len(response) > 200:
            score = 0.6
            issues.append("Missing legal disclaimer")
        else:
            score = 1.0

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Ethics check: disclaimer={'present' if has_disclaimer else 'missing'}",
            issues=issues,
        )


class BiasVerifier(Verifier):
    """Checks for potential bias in language."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        bias_indicators = ["obviously", "clearly", "undoubtedly", "without question"]
        bias_count = sum(1 for b in bias_indicators if b in response.lower())
        if bias_count > 2:
            score = 0.6
            issues.append("Potentially biased language detected")
        else:
            score = 1.0

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Bias check: {bias_count} bias indicators",
            issues=issues,
        )


class LanguageVerifier(Verifier):
    """Verifies language quality and clarity."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        # Check for overly complex sentences
        sentences = response.split(".")
        avg_sentence_len = (
            sum(len(s.split()) for s in sentences) / len(sentences)
            if sentences else 0
        )
        if avg_sentence_len > 40:
            score = 0.6
            issues.append(f"Average sentence length too long ({avg_sentence_len:.0f} words)")
        elif avg_sentence_len < 5:
            score = 0.5
            issues.append("Sentences too short")
        else:
            score = 1.0

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Language check: avg sentence length {avg_sentence_len:.0f} words",
            issues=issues,
        )


class HallucinationVerifier(Verifier):
    """Checks for potential hallucinated case law or statutes."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        # Flag case citations that look suspicious (very specific without context)
        case_patterns = re.findall(r"(\d{4}\s+\d+\s+\w+\s+\d+)", response)
        suspicious = 0
        for case in case_patterns:
            # Flag if year is implausible
            try:
                year = int(case[:4])
                if year > 2026 or year < 1800:
                    suspicious += 1
                    issues.append(f"Suspicious case citation year: {year}")
            except ValueError:
                pass

        score = max(0.0, 1.0 - (suspicious * 0.25))
        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Hallucination check: {suspicious} suspicious citations",
            issues=issues,
        )


class PrecedentVerifier(Verifier):
    """Verifies precedent hierarchy is respected."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        sc_mentions = len(re.findall(r"Supreme Court|SCC|AIR\s*SC", response, re.IGNORECASE))
        hc_mentions = len(re.findall(r"High Court", response, re.IGNORECASE))

        score = 1.0
        if sc_mentions > 0 and hc_mentions > 0:
            score = 1.0  # Good - mentions multiple levels
        elif sc_mentions > 0 or hc_mentions > 0:
            score = 0.8
        else:
            score = 0.6
            issues.append("No precedent hierarchy references")

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Precedent check: SC={sc_mentions}, HC={hc_mentions}",
            issues=issues,
        )


class LogicalFlowVerifier(Verifier):
    """Verifies logical flow and structure of arguments."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        paragraphs = [p for p in response.split("\n\n") if p.strip()]
        if len(paragraphs) < 2:
            score = 0.6
            issues.append("Response lacks paragraph structure")
        else:
            # Check for conclusion indicators at the end
            last_para = paragraphs[-1].lower()
            has_conclusion = any(c in last_para for c in [
                "in conclusion", "therefore", "in summary", "to conclude",
                "in light of", "accordingly", "thus"
            ])
            score = 1.0 if has_conclusion else 0.7
            if not has_conclusion:
                issues.append("No clear conclusion indicator")

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Logical flow check: {len(paragraphs)} paragraphs",
            issues=issues,
        )


class FactualVerifier(Verifier):
    """Verifies factual claims are supportable."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        # Check for specific dates, amounts, or numbers
        numbers = re.findall(r"\b\d{4}\b", response)  # years
        amounts = re.findall(r"₹\s*[\d,]+|\$\s*[\d,]+", response)

        score = 1.0
        if len(numbers) > 5 and not any(c in response.lower() for c in ["act", "section"]):
            score -= 0.2
            issues.append("Many numerical claims without statutory context")
        if amounts and " crore" not in response.lower() and "lakh" not in response.lower():
            score -= 0.1

        score = max(0.0, score)
        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Factual check: {len(numbers)} dates, {len(amounts)} amounts",
            issues=issues,
        )


class ComplianceVerifier(Verifier):
    """Verifies regulatory compliance mentions."""
    def verify(self, response: str, context: Optional[dict] = None) -> VerificationResult:
        issues: List[str] = []
        compliance_terms = ["compliance", "regulation", "regulatory", "statutory requirement",
                           "mandatory", "obligation", "penalty", "fine"]
        found = sum(1 for t in compliance_terms if t in response.lower())

        if found >= 2:
            score = 1.0
        elif found == 1:
            score = 0.7
        else:
            score = 0.5
            issues.append("No compliance language detected")

        passed = score >= self.min_score
        return self._base_result(
            passed=passed, score=score,
            details=f"Compliance check: {found} compliance terms",
            issues=issues,
        )


class VerifierRegistry:
    """Registry managing all 15 verifiers."""

    def __init__(self) -> None:
        self.verifiers: Dict[str, Verifier] = {}
        self._initialize_verifiers()

    def _initialize_verifiers(self) -> None:
        """Create all 15 verifiers."""
        verifier_classes = [
            (VerifierType.ACCURACY, "AccuracyGuard", AccuracyVerifier, "Checks factual accuracy of legal claims", 1.5),
            (VerifierType.CITATION, "CitationCheck", CitationVerifier, "Verifies presence of legal citations", 1.5),
            (VerifierType.REASONING, "ReasoningFlow", ReasoningVerifier, "Validates logical reasoning structure", 1.3),
            (VerifierType.COMPLETENESS, "CompleteCheck", CompletenessVerifier, "Ensures response completeness", 1.0),
            (VerifierType.CONSISTENCY, "ConsistGuard", ConsistencyVerifier, "Checks internal consistency", 1.2),
            (VerifierType.JURISDICTION, "JurisdictionPro", JurisdictionVerifier, "Verifies jurisdiction appropriateness", 1.1),
            (VerifierType.STATUTORY, "StatutoryRef", StatutoryVerifier, "Validates statutory references", 1.3),
            (VerifierType.ETHICS, "EthicsShield", EthicsVerifier, "Ensures ethical considerations", 1.0),
            (VerifierType.BIAS, "BiasGuardian", BiasVerifier, "Detects potential bias", 0.9),
            (VerifierType.LANGUAGE, "LanguagePro", LanguageVerifier, "Checks language quality", 0.8),
            (VerifierType.HALLUCINATION, "HallucGuard", HallucinationVerifier, "Detects hallucinated citations", 1.4),
            (VerifierType.PRECEDENT, "PrecedentCheck", PrecedentVerifier, "Verifies precedent hierarchy", 1.0),
            (VerifierType.LOGICAL_FLOW, "FlowGuard", LogicalFlowVerifier, "Validates argument flow", 1.1),
            (VerifierType.FACTUAL, "FactCheckPro", FactualVerifier, "Verifies factual claims", 1.2),
            (VerifierType.COMPLIANCE, "ComplianceGuard", ComplianceVerifier, "Checks regulatory compliance", 1.1),
        ]

        for idx, (vtype, name, cls, desc, weight) in enumerate(verifier_classes, 1):
            v_id = f"VERIF-{idx:02d}"
            verifier = cls(
                verifier_id=v_id,
                name=name,
                verifier_type=vtype,
                description=desc,
                weight=weight,
            )
            self.verifiers[v_id] = verifier

    def get_all(self) -> List[Verifier]:
        return list(self.verifiers.values())

    def get_by_id(self, verifier_id: str) -> Optional[Verifier]:
        return self.verifiers.get(verifier_id)

    def verify_response(self, response: str, context: Optional[dict] = None) -> List[VerificationResult]:
        """Run all enabled verifiers on a response."""
        # Guard against None/empty responses — don't crash the pipeline
        if response is None:
            response = ""
        if not isinstance(response, str):
            response = str(response) if response else ""
        results: List[VerificationResult] = []
        # If response is empty, skip verification — all verifiers will fail on .lower() anyway
        if not response.strip():
            for verifier in self.verifiers.values():
                if verifier.enabled:
                    results.append(VerificationResult(
                        verifier_id=verifier.verifier_id,
                        verifier_name=verifier.name,
                        verifier_type=verifier.verifier_type,
                        passed=False,
                        score=0.0,
                        details="Skipped: empty response",
                        issues=["Response was empty — verification skipped"],
                    ))
            return results
        for verifier in self.verifiers.values():
            if verifier.enabled:
                try:
                    result = verifier.verify(response, context)
                    results.append(result)
                except Exception as e:
                    results.append(VerificationResult(
                        verifier_id=verifier.verifier_id,
                        verifier_name=verifier.name,
                        verifier_type=verifier.verifier_type,
                        passed=False,
                        score=0.0,
                        details=f"Verifier error: {e}",
                        issues=["Verifier execution failed"],
                    ))
        return results

    def get_verification_summary(self, results: List[VerificationResult]) -> dict:
        """Generate a summary of verification results."""
        if not results:
            return {"overall_passed": False, "overall_score": 0.0, "verifier_count": 0}

        total_weight = 0.0
        weighted_score = 0.0
        passed_count = 0
        all_issues: List[str] = []

        for result in results:
            verifier = self.verifiers.get(result.verifier_id)
            weight = verifier.weight if verifier else 1.0
            total_weight += weight
            weighted_score += result.score * weight
            if result.passed:
                passed_count += 1
            all_issues.extend(result.issues)

        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0
        overall_passed = overall_score >= settings.COMPLIANCE_MIN_SCORE and passed_count >= len(results) * 0.6

        return {
            "overall_passed": overall_passed,
            "overall_score": round(overall_score, 4),
            "verifiers_passed": passed_count,
            "verifiers_total": len(results),
            "pass_rate": round(passed_count / len(results) * 100, 1) if results else 0.0,
            "issues_found": all_issues,
            "issue_count": len(all_issues),
        }

    def stats(self) -> dict:
        total_checks = sum(v.checks_run for v in self.verifiers.values())
        total_passed = sum(v.checks_passed for v in self.verifiers.values())
        return {
            "total_verifiers": len(self.verifiers),
            "enabled": sum(1 for v in self.verifiers.values() if v.enabled),
            "total_checks_run": total_checks,
            "total_checks_passed": total_passed,
            "overall_pass_rate": round(total_passed / total_checks * 100, 1) if total_checks else 0.0,
        }

    def to_dict(self) -> List[dict]:
        return [v.to_dict() for v in self.verifiers.values()]


# Singleton
verifier_registry = VerifierRegistry()
