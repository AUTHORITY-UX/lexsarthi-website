# Copyright (c) 2025 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# THE ADVOCACY A LAW FIRM is the sole owner and title holder of this software.

from schemas import LegalAgentOutput

class VerifierAgent:
    def verify(self, output: LegalAgentOutput, original_context: str):
        issues = []
        score = 100

        # 1. Citation integrity (anti-hallucination)
        if output.status == "success" and len(output.citations) == 0:
            issues.append("CRITICAL: No citations for SUCCESS status.")
            score -= 50
        else:
            for idx, cit in enumerate(output.citations):
                if cit.source.lower() in ["source", "reference", "unknown", "document"]:
                    issues.append(f"Citation #{idx+1}: generic source '{cit.source}'")
                    score -= 15
                if len(cit.excerpt) < 10:
                    issues.append(f"Citation #{idx+1}: excerpt too short")
                    score -= 10
                if original_context and cit.excerpt not in original_context:
                    issues.append(f"Citation #{idx+1}: HALLUCINATION - excerpt not found in document")
                    score -= 30

        # 2. Confidence vs evidence
        if output.confidence_score > 0.9 and len(output.citations) < 2:
            issues.append(f"High confidence ({output.confidence_score}) but only {len(output.citations)} citations.")
            score -= 20

        # 3. Status vs confidence mismatch
        if output.status == "partial" and output.confidence_score > 0.8:
            issues.append("Status 'partial' but confidence > 0.8 – mismatch.")
            score -= 15

        final_score = max(0, min(100, score))
        is_valid = final_score >= 60 and "CRITICAL" not in " ".join(issues)

        if final_score >= 85:
            badge = "✅ Verified"
        elif final_score >= 60:
            badge = "⚠️ Partial"
        else:
            badge = "❌ Not Verified"

        return is_valid, final_score, issues, badge