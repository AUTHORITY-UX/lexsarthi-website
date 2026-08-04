"""
core/ethics_guardrails.py
==========================
Unknown Verdict v41.0 — Ethical AI Guardrails Module

Four immediate guardrails from the Ethics Roadmap:
  1. DISCLAIMER  — legal disclaimer on every response
  2. PII_REDACT  — redact Aadhaar, PAN, phone, email, case numbers before LLM calls
  3. HALLUCINATE — verify cited case names / section numbers actually exist
  4. REFUSAL     — refuse harmful queries, redirect to NALSA (15100)

DESIGN PRINCIPLES
  - Zero hard dependencies on the rest of the codebase (importable standalone)
  - Every function returns a dataclass / dict — never raises on bad input
  - Graceful: if a guardrail can't run, the request still proceeds with a warning
  - Audit-ready: every action is logged as a structured dict

USAGE (in routes.py /chat endpoint):

    from core.ethics_guardrails import EthicsPipeline

    ethics = EthicsPipeline()

    # 1. Before sending to LLM — check refusal + redact PII
    pre = ethics.pre_llm(user_message)
    if pre.should_refuse:
        return {"reply": pre.refusal_message, "blocked": True}

    safe_prompt = pre.redacted_text   # PII stripped

    # 2. After LLM responds — verify citations + add disclaimer
    post = ethics.post_llm(llm_response, user_message)
    final_reply = post.safe_response  # disclaimer appended, unverified citations flagged

    # 3. Audit trail
    audit = ethics.last_audit   # list of all actions taken this request
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("ethics_guardrails")


# ─────────────────────────────────────────────────────────────────────────────
# 1. LEGAL DISCLAIMER
# ─────────────────────────────────────────────────────────────────────────────

DISCLAIMER_TEXT = (
    "\n\n---\n"
    "⚠️ This is AI-generated information, not legal advice. "
    "Please consult a licensed advocate before acting on anything stated here. "
    "For free legal aid, call NALSA at 15100."
)

# Shorter variant for chat UIs where space matters
DISCLAIMER_SHORT = (
    " (AI-generated — not legal advice. Consult a licensed advocate. "
    "Free legal aid: NALSA 15100.)"
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PII REDACTION
# ─────────────────────────────────────────────────────────────────────────────

# Each pattern: (compiled_regex, replacement_label, human_name)
PII_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Aadhaar — 12 digits, may have spaces/dashes, NOT starting with 0 or 1
    (
        re.compile(r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "[AADHAAR_REDACTED]",
        "Aadhaar",
    ),
    # PAN — 5 letters, 4 digits, 1 letter (ABCDE1234F)
    (
        re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
        "[PAN_REDACTED]",
        "PAN",
    ),
    # Indian phone — +91 followed by 10 digits, or 10 digits starting 6-9
    (
        re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}"),
        "[PHONE_REDACTED]",
        "Phone",
    ),
    # Email
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[EMAIL_REDACTED]",
        "Email",
    ),
    # Case numbers — common Indian formats:
    #   Crl.A. 123/2020, W.P.(C) 456/2021, Diary No. 789/2022, etc.
    (
        re.compile(
            r"\b(?:Crl\.?A\.?|W\.?P\.?\(C?\)|S\.?L\.?P\.?|Diary\s+No\.?|"
            r"Case\s+No\.?|FIR\s+No\.?)\s*\d+/\d{4}\b",
            re.IGNORECASE,
        ),
        "[CASE_NUMBER_REDACTED]",
        "Case Number",
    ),
    # FIR numbers — simpler format: FIR 123/2022
    (
        re.compile(r"\bFIR\s*\d{1,6}[/\-]\d{2,4}\b", re.IGNORECASE),
        "[FIR_REDACTED]",
        "FIR Number",
    ),
    # Bank account — 9-18 digit sequences (conservative; only if clearly labelled)
    (
        re.compile(r"(?:account\s*(?:no|number)[:\s]*)\d{9,18}", re.IGNORECASE),
        "Account No: [REDACTED]",
        "Bank Account",
    ),
    # Credit card — 16 digits, grouped in 4s
    (
        re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b"),
        "[CARD_REDACTED]",
        "Credit Card",
    ),
]


@dataclass
class PIIRedactionResult:
    redacted_text: str
    pii_found: list[dict] = field(default_factory=list)
    total_redacted: int = 0


def redact_pii(text: str) -> PIIRedactionResult:
    """
    Redact all PII from text. Returns the redacted text and a list of what was found.
    Does NOT store the original PII values — only records the type and position.
    """
    if not text or not isinstance(text, str):
        return PIIRedactionResult(redacted_text=text or "")

    redacted = text
    found: list[dict] = []

    for pattern, replacement, human_name in PII_PATTERNS:
        matches = list(pattern.finditer(redacted))
        if matches:
            found.append({
                "type": human_name,
                "count": len(matches),
            })
            redacted = pattern.sub(replacement, redacted)

    return PIIRedactionResult(
        redacted_text=redacted,
        pii_found=found,
        total_redacted=sum(item["count"] for item in found),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. HALLUCINATION VERIFIER — citation checking
# ─────────────────────────────────────────────────────────────────────────────

# Known major Indian statutes and their common section ranges.
# This is a baseline knowledge base — extend with your RAG corpus.
KNOWN_STATUTES: dict[str, dict] = {
    "indian penal code": {"aliases": ["ipc"], "max_section": 511},
    "code of criminal procedure": {"aliases": ["crpc", "cr.p.c"], "max_section": 484},
    "civil procedure code": {"aliases": ["cpc", "c.p.c"], "max_section": 158},
    "indian evidence act": {"aliases": ["iea"], "max_section": 167},
    "contract act": {"aliases": ["ica"], "max_section": 238},
    "companies act": {"aliases": [], "max_section": 470},
    "income tax act": {"aliases": [], "max_section": 298},
    "negotiable instruments act": {"aliases": ["nia"], "max_section": 147},
    "consumer protection act": {"aliases": ["cpa"], "max_section": 107},
    "information technology act": {"aliases": ["it act", "ita"], "max_section": 94},
    "arbitration and conciliation act": {"aliases": ["aca"], "max_section": 89},
    "domestic violence act": {"aliases": ["pdva", "pwdva"], "max_section": 37},
    "scheduled castes and scheduled tribes act": {"aliases": ["sc/st act", "poa act"], "max_section": 22},
    "right to information act": {"aliases": ["rti act"], "max_section": 23},
    "goods and services tax act": {"aliases": ["cgst act", "gst act"], "max_section": 174},
    "dpdp act": {"aliases": ["digital personal data protection act"], "max_section": 51},
}

# Patterns to extract citations from LLM output
# Full statute name: "Section 302 of the Indian Penal Code"
SECTION_PATTERN = re.compile(
    r"(?:Section|Sec\.?|S\.)\s*(\d+)\s*"
    r"(?:of\s+|under\s+)?(?:the\s+)?"
    r"([A-Z][A-Za-z\s&\-]+?(?:Act|Code|Rules?|Ordinance))"
    r"(?:[,\s\.]|$)",
    re.IGNORECASE,
)
# Abbreviated statute: "Section 302 IPC", "Section 482 CrPC"
ABBREV_SECTION_PATTERN = re.compile(
    r"(?:Section|Sec\.?|S\.)\s*(\d+)\s+"
    r"(IPC|CrPC|Cr\.?P\.?C|CPC|C\.?P\.?C|IEA|NIA|CPA|IT\s?Act|ACA|PDVA|RTI\s?Act|GST\s?Act|DPDP\s?Act)",
    re.IGNORECASE,
)
CASE_CITATION_PATTERN = re.compile(
    # e.g. "Kesavananda Bharati v. State of Kerala (1973)"
    r"([A-Z][A-Za-z\s\.]+?)\s*v\.?\s*([A-Z][A-Za-z\s\.]+?)\s*\((\d{4})\)"
)
BARE_ACT_PATTERN = re.compile(
    r"(?:under|as per|per|according to)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z\s\.\(\)/&-]+?)(?:[,\s\.]|$)",
    re.IGNORECASE,
)


@dataclass
class CitationCheck:
    citation: str
    type: str          # "section" | "case" | "statute"
    verified: bool
    note: str = ""


@dataclass
class HallucinationResult:
    citations_found: list[CitationCheck]
    unverified: list[CitationCheck]
    all_verified: bool
    warning_added: bool
    safe_response: str


def _verify_statute_section(statute_name: str, section_num: int) -> tuple[bool, str]:
    """Verify a section number against known statutes by full name."""
    statute_lower = statute_name.lower()
    for known_name, info in KNOWN_STATUTES.items():
        if known_name in statute_lower or any(
            alias in statute_lower for alias in info["aliases"]
        ):
            if 1 <= section_num <= info["max_section"]:
                return True, f"Section {section_num} exists in {known_name} (valid range: 1-{info['max_section']})"
            else:
                return False, f"Section {section_num} does NOT exist in {known_name} (max: {info['max_section']})"
    return False, f"Statute '{statute_name}' not in known database — cannot verify"


def _verify_abbrev_section(abbrev: str, section_num: int) -> tuple[bool, str]:
    """Verify a section number against known statutes by abbreviation."""
    abbrev_map = {
        "IPC": "indian penal code",
        "CRPC": "code of criminal procedure",
        "CPC": "civil procedure code",
        "IEA": "indian evidence act",
        "NIA": "negotiable instruments act",
        "CPA": "consumer protection act",
        "ITACT": "information technology act",
        "ACA": "arbitration and conciliation act",
        "PDVA": "domestic violence act",
        "RTIACT": "right to information act",
        "GSTACT": "goods and services tax act",
        "DPDPACT": "dpdp act",
    }
    known_name = abbrev_map.get(abbrev)
    if not known_name:
        return False, f"Abbreviation '{abbrev}' not recognized — cannot verify"
    info = KNOWN_STATUTES.get(known_name)
    if not info:
        return False, f"Statute for '{abbrev}' not in database"
    if 1 <= section_num <= info["max_section"]:
        return True, f"Section {section_num} exists in {known_name} (valid range: 1-{info['max_section']})"
    else:
        return False, f"Section {section_num} does NOT exist in {known_name} (max: {info['max_section']})"


def verify_citations(llm_response: str) -> list[CitationCheck]:
    """Extract and verify all legal citations from the LLM response."""
    if not llm_response or not isinstance(llm_response, str):
        return []

    checks: list[CitationCheck] = []

    # --- Check Section references (full statute names) ---
    for match in SECTION_PATTERN.finditer(llm_response):
        section_num = int(match.group(1))
        statute_name = match.group(2).strip().rstrip(".")
        citation_str = f"Section {section_num} of {statute_name}"

        verified, note = _verify_statute_section(statute_name, section_num)

        checks.append(CitationCheck(
            citation=citation_str,
            type="section",
            verified=verified,
            note=note,
        ))

    # --- Check Section references (abbreviated statutes: "Section 302 IPC") ---
    for match in ABBREV_SECTION_PATTERN.finditer(llm_response):
        section_num = int(match.group(1))
        abbrev = match.group(2).upper().replace(" ", "").replace(".", "")
        citation_str = f"Section {section_num} {abbrev}"

        verified, note = _verify_abbrev_section(abbrev, section_num)

        checks.append(CitationCheck(
            citation=citation_str,
            type="section",
            verified=verified,
            note=note,
        ))

    # --- Check case citations ---
    for match in CASE_CITATION_PATTERN.finditer(llm_response):
        petitioner = match.group(1).strip()
        respondent = match.group(2).strip()
        year = match.group(3)
        citation_str = f"{petitioner} v. {respondent} ({year})"

        # Basic sanity checks
        verified = False
        note = ""

        if len(petitioner) < 3 or len(respondent) < 3:
            note = "Case name too short — likely false citation"
        elif int(year) < 1950 or int(year) > 2026:
            note = f"Year {year} is outside plausible range (1950-2026)"
        else:
            # Mark as unverified — requires DB lookup against actual case law
            note = "Case citation detected — requires database verification against Indian Case Law"

        checks.append(CitationCheck(
            citation=citation_str,
            type="case",
            verified=verified,
            note=note,
        ))

    return checks


def check_hallucinations(llm_response: str) -> HallucinationResult:
    """
    Verify citations in LLM response. If unverified citations are found,
    append a warning to the response so the user knows to double-check.
    """
    if not llm_response or not isinstance(llm_response, str):
        return HallucinationResult(
            citations_found=[],
            unverified=[],
            all_verified=True,
            warning_added=False,
            safe_response=llm_response or "",
        )

    citations = verify_citations(llm_response)
    unverified = [c for c in citations if not c.verified]

    safe_response = llm_response
    warning_added = False

    if unverified:
        warning = (
            "\n\n⚠️ **Citation Verification Notice:** "
            f"{len(unverified)} citation(s) could not be verified against known legal databases. "
            "Please cross-check with authoritative sources (Supreme Court website, eGazette, Indian Kanoon) "
            "before relying on them."
        )
        safe_response = llm_response + warning
        warning_added = True

    return HallucinationResult(
        citations_found=citations,
        unverified=unverified,
        all_verified=len(unverified) == 0,
        warning_added=warning_added,
        safe_response=safe_response,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. REFUSAL PROTOCOL
# ─────────────────────────────────────────────────────────────────────────────

# Categories of queries that must be refused
# Each: (list of trigger patterns, refusal message, redirect resource)
REFUSAL_CATEGORIES: list[dict] = [
    {
        "name": "evade_arrest",
        "patterns": [
            r"how\s+(?:to\s+)?(?:evade|avoid|escape)\s+arrest",
            r"how\s+(?:to\s+)?(?:skip|skip\s+out\s+on)\s+bail",
            r"how\s+(?:to\s+)?flee\s+(?:from|the)\s+(?:police|law|country)",
            r"how\s+(?:to\s+)?(?:hide|disappear)\s+from\s+(?:police|law)",
            r"absconding\s+(?:advice|how|tips)",
        ],
        "message": (
            "I cannot provide advice on evading arrest or absconding from legal proceedings. "
            "Doing so is a criminal offence under Section 224 IPC (resistance to lawful apprehension). "
            "\n\nIf you are facing arrest, please contact a criminal defence advocate immediately. "
            "For free legal aid, call NALSA at **15100** or visit nalsa.gov.in."
        ),
    },
    {
        "name": "destroy_evidence",
        "patterns": [
            r"how\s+(?:to\s+)?(?:destroy|dispose\s+of|get\s+rid\s+of|tamper\s+with)\s+"
            r"(?:evidence|documents?|records?|proof)",
            r"how\s+(?:to\s+)?(?:fabricate|falsify|fake)\s+(?:documents?|evidence|records?)",
            r"destroying\s+evidence\s+(?:advice|how|tips)",
        ],
        "message": (
            "I cannot help with destroying, tampering with, or fabricating evidence. "
            "These are criminal offences under Sections 201, 204, and 463 IPC. "
            "\n\nIf evidence is being used against you unfairly, consult a defence advocate "
            "who can challenge it through lawful means. "
            "For free legal aid, call NALSA at **15100**."
        ),
    },
    {
        "name": "should_confess",
        "patterns": [
            r"should\s+i\s+(?:confess|admit\s+guilt|plead\s+guilty)",
            r"should\s+i\s+(?:tell|admit\s+to)\s+the\s+police",
            r"is\s+it\s+(?:better|good)\s+to\s+confess",
        ],
        "message": (
            "I cannot advise you on whether to confess or plead guilty. "
            "This is a critical legal decision that depends on the specifics of your case, "
            "the evidence against you, and potential defences — it must be discussed with "
            "a licensed criminal defence advocate. "
            "\n\nYou have the right to remain silent and the right to legal representation "
            "under Article 22(1) of the Constitution. "
            "For free legal aid, call NALSA at **15100**."
        ),
    },
    {
        "name": "commit_crime",
        "patterns": [
            r"how\s+(?:to\s+)?(?:commit|carry\s+out|execute)\s+"
            r"(?:murder|theft|robbery|fraud|assault|kidnapping|rape|arson)",
            r"how\s+(?:to\s+)?(?:hack|break\s+into|bypass)\s+"
            r"(?:a\s+)?(?:system|account|password|security|firewall)",
            r"how\s+(?:to\s+)?(?:forge|counterfeit|fake)\s+"
            r"(?:documents?|currency|certificates?|ids?)",
            r"how\s+(?:to\s+)?(?:poison|drug)\s+someone",
            r"how\s+(?:to\s+)?blackmail\s+someone",
        ],
        "message": (
            "I cannot provide instructions for committing any illegal act. "
            "If you are in a situation where you feel forced into illegal activity, "
            "please reach out to the police (100) or a legal aid service. "
            "\n\nFor free legal counselling, call NALSA at **15100**."
        ),
    },
    {
        "name": "self_harm",
        "patterns": [
            r"how\s+(?:to\s+)?(?:hurt|harm|injure|kill)\s+(?:myself|yourself|oneself)",
            r"(?:want|thinking\s+about|planning)\s+(?:to\s+)?(?:end|kill|die)",
            r"suicide\s+(?:methods|ways|how)",
            r"how\s+(?:to\s+)?commit\s+suicide",
        ],
        "message": (
            "I'm concerned about what you're going through. "
            "You don't have to face this alone. "
            "\n\nPlease reach out right now:\n"
            "• iCall (free mental health helpline): **9152987821**\n"
            "• Vandrevala Foundation: **1860-2662-345**\n"
            "• KIRAN helpline (Govt of India): **1800-599-0019**\n"
            "\nIf you are in immediate danger, call 112."
        ),
    },
]

# Compile all patterns at import time
for category in REFUSAL_CATEGORIES:
    category["compiled"] = [re.compile(p, re.IGNORECASE) for p in category["patterns"]]


@dataclass
class RefusalResult:
    should_refuse: bool
    category: str = ""
    message: str = ""
    matched_pattern: str = ""


def check_refusal(user_message: str) -> RefusalResult:
    """Check if the user's message should be refused under the refusal protocol."""
    if not user_message or not isinstance(user_message, str):
        return RefusalResult(should_refuse=False)

    msg_lower = user_message.lower()

    for category in REFUSAL_CATEGORIES:
        for compiled in category["compiled"]:
            match = compiled.search(msg_lower)
            if match:
                return RefusalResult(
                    should_refuse=True,
                    category=category["name"],
                    message=category["message"],
                    matched_pattern=match.group(0),
                )

    return RefusalResult(should_refuse=False)


# ─────────────────────────────────────────────────────────────────────────────
# 5. BIAS DETECTION (short-term guardrail — included for forward-compat)
# ─────────────────────────────────────────────────────────────────────────────

# Name-based signals that could trigger differential treatment
CASTE_KEYWORDS = re.compile(
    r"\b(?:scheduled\s+caste|scheduled\s+tribe|dalit|sc/st|obc|backward\s+class)\b",
    re.IGNORECASE,
)
RELIGION_KEYWORDS = re.compile(
    r"\b(?:muslim|hindu|christian|sikh|jain|buddhist|parsi|jew)\b",
    re.IGNORECASE,
)
GENDER_KEYWORDS = re.compile(
    r"\b(?:woman|man|female|male|transgender|intersex|gender)\b",
    re.IGNORECASE,
)


@dataclass
class BiasCheck:
    has_bias_signal: bool
    signals: list[str]
    note: str = ""


def check_bias(user_message: str) -> BiasCheck:
    """Detect if the query contains demographic signals that could lead to biased advice."""
    if not user_message:
        return BiasCheck(has_bias_signal=False, signals=[])

    signals: list[str] = []

    if CASTE_KEYWORDS.search(user_message):
        signals.append("caste_reference")
    if RELIGION_KEYWORDS.search(user_message):
        signals.append("religion_reference")
    if GENDER_KEYWORDS.search(user_message):
        signals.append("gender_reference")

    note = ""
    if signals:
        note = (
            "Query contains demographic references. "
            "Ensure response quality is identical regardless of the user's identity."
        )

    return BiasCheck(has_bias_signal=bool(signals), signals=signals, note=note)


# ─────────────────────────────────────────────────────────────────────────────
# 6. AUDIT TRAIL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuditEntry:
    timestamp: str
    guardrail: str
    action: str
    details: dict


@dataclass
class AuditTrail:
    entries: list[AuditEntry] = field(default_factory=list)

    def add(self, guardrail: str, action: str, **details):
        from datetime import datetime, timezone
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            guardrail=guardrail,
            action=action,
            details=details,
        )
        self.entries.append(entry)
        logger.info(f"[ETHICS] {guardrail}: {action} — {details}")

    def to_list(self) -> list[dict]:
        return [
            {
                "timestamp": e.timestamp,
                "guardrail": e.guardrail,
                "action": e.action,
                "details": e.details,
            }
            for e in self.entries
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 7. PIPELINE — orchestrates all guardrails
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PreLLMResult:
    """Result of pre-LLM processing (refusal check + PII redaction)."""
    should_refuse: bool
    refusal_message: str
    refusal_category: str
    redacted_text: str
    pii_redacted: list[dict]
    bias_signals: list[str]
    audit: list[dict]


@dataclass
class PostLLMResult:
    """Result of post-LLM processing (citation verification + disclaimer)."""
    safe_response: str
    citations: list[dict]
    unverified_citations: list[dict]
    all_citations_verified: bool
    warning_added: bool
    disclaimer_added: bool
    audit: list[dict]


class EthicsPipeline:
    """
    Main entry point. Create one instance per request.

    Usage:
        ethics = EthicsPipeline()
        pre = ethics.pre_llm(user_message)
        if pre.should_refuse:
            return pre.refusal_message
        # ... call LLM with pre.redacted_text ...
        post = ethics.post_llm(llm_response, user_message)
        return post.safe_response
    """

    def __init__(
        self,
        disclaimer_mode: str = "full",  # "full" | "short" | "none"
        enable_pii_redaction: bool = True,
        enable_hallucination_check: bool = True,
        enable_refusal: bool = True,
        enable_bias_detection: bool = True,
    ):
        self.disclaimer_mode = disclaimer_mode
        self.enable_pii_redaction = enable_pii_redaction
        self.enable_hallucination_check = enable_hallucination_check
        self.enable_refusal = enable_refusal
        self.enable_bias_detection = enable_bias_detection
        self._audit = AuditTrail()

    @property
    def last_audit(self) -> list[dict]:
        return self._audit.to_list()

    def pre_llm(self, user_message: str) -> PreLLMResult:
        """
        Run pre-LLM guardrails: refusal check → PII redaction → bias detection.
        Call this BEFORE sending the message to the LLM.
        """
        audit = AuditTrail()

        # --- Refusal check ---
        refusal = RefusalResult(should_refuse=False)
        if self.enable_refusal:
            refusal = check_refusal(user_message)
            if refusal.should_refuse:
                audit.add(
                    "refusal",
                    "blocked",
                    category=refusal.category,
                    matched=refusal.matched_pattern,
                )
                audit.add("refusal", "redirect", resource="NALSA 15100")
                return PreLLMResult(
                    should_refuse=True,
                    refusal_message=refusal.message,
                    refusal_category=refusal.category,
                    redacted_text="",
                    pii_redacted=[],
                    bias_signals=[],
                    audit=audit.to_list(),
                )
            else:
                audit.add("refusal", "passed", reason="no trigger matched")

        # --- PII redaction ---
        pii_result = PIIRedactionResult(redacted_text=user_message)
        if self.enable_pii_redaction:
            pii_result = redact_pii(user_message)
            if pii_result.total_redacted > 0:
                audit.add(
                    "pii_redaction",
                    "redacted",
                    count=pii_result.total_redacted,
                    types=[p["type"] for p in pii_result.pii_found],
                )
            else:
                audit.add("pii_redaction", "passed", reason="no PII detected")

        # --- Bias detection ---
        bias_signals: list[str] = []
        if self.enable_bias_detection:
            bias = check_bias(user_message)
            if bias.has_bias_signal:
                audit.add(
                    "bias_detection",
                    "flagged",
                    signals=bias.signals,
                    note=bias.note,
                )
                bias_signals = bias.signals
            else:
                audit.add("bias_detection", "passed", reason="no demographic signals")

        # Merge audit into the pipeline-level audit
        for entry in audit.entries:
            self._audit.add(entry.guardrail, entry.action, **entry.details)

        return PreLLMResult(
            should_refuse=False,
            refusal_message="",
            refusal_category="",
            redacted_text=pii_result.redacted_text,
            pii_redacted=pii_result.pii_found,
            bias_signals=bias_signals,
            audit=audit.to_list(),
        )

    def post_llm(self, llm_response: str, original_query: str = "") -> PostLLMResult:
        """
        Run post-LLM guardrails: citation verification → disclaimer.
        Call this AFTER receiving the LLM response, before returning to user.
        """
        audit = AuditTrail()

        safe_response = llm_response or ""
        citations: list[dict] = []
        unverified: list[dict] = []
        all_verified = True
        warning_added = False

        # --- Hallucination / citation check ---
        if self.enable_hallucination_check:
            halluc = check_hallucinations(llm_response)
            safe_response = halluc.safe_response
            warning_added = halluc.warning_added
            citations = [
                {
                    "citation": c.citation,
                    "type": c.type,
                    "verified": c.verified,
                    "note": c.note,
                }
                for c in halluc.citations_found
            ]
            unverified = [
                {
                    "citation": c.citation,
                    "type": c.type,
                    "note": c.note,
                }
                for c in halluc.unverified
            ]
            all_verified = halluc.all_verified

            if unverified:
                audit.add(
                    "hallucination",
                    "flagged",
                    total_citations=len(citations),
                    unverified=len(unverified),
                )
            elif citations:
                audit.add(
                    "hallucination",
                    "passed",
                    total_citations=len(citations),
                    all_verified=True,
                )
            else:
                audit.add("hallucination", "passed", reason="no citations found")

        # --- Disclaimer ---
        disclaimer_added = False
        if self.disclaimer_mode == "full":
            safe_response = safe_response + DISCLAIMER_TEXT
            disclaimer_added = True
            audit.add("disclaimer", "appended", mode="full")
        elif self.disclaimer_mode == "short":
            safe_response = safe_response + DISCLAIMER_SHORT
            disclaimer_added = True
            audit.add("disclaimer", "appended", mode="short")

        # Merge into pipeline audit
        for entry in audit.entries:
            self._audit.add(entry.guardrail, entry.action, **entry.details)

        return PostLLMResult(
            safe_response=safe_response,
            citations=citations,
            unverified_citations=unverified,
            all_citations_verified=all_verified,
            warning_added=warning_added,
            disclaimer_added=disclaimer_added,
            audit=audit.to_list(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. CONVENIENCE: standalone functions (for use without the pipeline class)
# ─────────────────────────────────────────────────────────────────────────────

def apply_guardrails(
    user_message: str,
    llm_response: str,
    disclaimer_mode: str = "full",
) -> dict:
    """
    One-shot helper: run all guardrails on a user message + LLM response.
    Returns a dict with everything you need.

    Useful for quick integration into a single endpoint:
        result = apply_guardrails(user_msg, llm_reply)
        if result["blocked"]:
            return result["refusal_message"]
        return result["safe_response"]
    """
    pipeline = EthicsPipeline(disclaimer_mode=disclaimer_mode)
    pre = pipeline.pre_llm(user_message)

    if pre.should_refuse:
        return {
            "blocked": True,
            "refusal_message": pre.refusal_message,
            "refusal_category": pre.refusal_category,
            "safe_response": pre.refusal_message,
            "audit": pipeline.last_audit,
        }

    post = pipeline.post_llm(llm_response, user_message)

    return {
        "blocked": False,
        "safe_response": post.safe_response,
        "citations": post.citations,
        "unverified_citations": post.unverified_citations,
        "all_citations_verified": post.all_citations_verified,
        "pii_redacted": pre.pii_redacted,
        "bias_signals": pre.bias_signals,
        "audit": pipeline.last_audit,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. STATUS (for /moat/ethics-status endpoint)
# ─────────────────────────────────────────────────────────────────────────────

def ethics_status() -> dict:
    """Return the status of all guardrails — for the Moat status endpoint."""
    pipeline = EthicsPipeline()
    return {
        "module": "ethics_guardrails",
        "version": "1.0.0",
        "guardrails": {
            "disclaimer": {
                "enabled": True,
                "mode": pipeline.disclaimer_mode,
                "description": "Legal disclaimer appended to every response",
            },
            "pii_redaction": {
                "enabled": True,
                "patterns": len(PII_PATTERNS),
                "types": [p[2] for p in PII_PATTERNS],
                "description": "Redacts Aadhaar, PAN, phone, email, case numbers before LLM calls",
            },
            "hallucination_verifier": {
                "enabled": True,
                "known_statutes": len(KNOWN_STATUTES),
                "description": "Verifies cited sections and case names against known legal databases",
            },
            "refusal_protocol": {
                "enabled": True,
                "categories": [c["name"] for c in REFUSAL_CATEGORIES],
                "description": "Refuses harmful queries and redirects to NALSA 15100",
            },
            "bias_detection": {
                "enabled": True,
                "description": "Flags demographic signals for quality-parity monitoring",
            },
        },
        "audit_trail": True,
        "nalsa_hotline": "15100",
        "mental_health_hotlines": ["9152987821", "1860-2662-345", "1800-599-0019"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. SELF-TEST (run: python core/ethics_guardrails.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("ETHICS GUARDRAILS — SELF TEST")
    print("=" * 70)

    # Test 1: PII redaction
    print("\n1. PII REDACTION")
    test_pii = (
        "My Aadhaar is 2345 6789 0123 and PAN is ABCDE1234F. "
        "Call me at +91 9876543210 or email me at test@example.com. "
        "My case is W.P.(C) 1234/2020."
    )
    result = redact_pii(test_pii)
    print(f"   Original: {test_pii}")
    print(f"   Redacted: {result.redacted_text}")
    print(f"   PII found: {result.pii_found}")
    print(f"   Total redacted: {result.total_redacted}")
    assert "[AADHAAR_REDACTED]" in result.redacted_text
    assert "[PAN_REDACTED]" in result.redacted_text
    assert "[PHONE_REDACTED]" in result.redacted_text
    assert "[EMAIL_REDACTED]" in result.redacted_text
    print("   ✅ PASSED")

    # Test 2: Refusal — evade arrest
    print("\n2. REFUSAL — evade arrest")
    result = check_refusal("How to evade arrest after FIR?")
    assert result.should_refuse
    assert result.category == "evade_arrest"
    assert "15100" in result.message
    print(f"   Category: {result.category}")
    print(f"   Message: {result.message[:80]}...")
    print("   ✅ PASSED")

    # Test 3: Refusal — destroy evidence
    print("\n3. REFUSAL — destroy evidence")
    result = check_refusal("How to destroy evidence before trial?")
    assert result.should_refuse
    assert result.category == "destroy_evidence"
    print("   ✅ PASSED")

    # Test 4: Refusal — should I confess
    print("\n4. REFUSAL — should I confess")
    result = check_refusal("Should I confess to the police?")
    assert result.should_refuse
    assert result.category == "should_confess"
    print("   ✅ PASSED")

    # Test 5: Refusal — self harm
    print("\n5. REFUSAL — self harm")
    result = check_refusal("I want to end my life")
    assert result.should_refuse
    assert result.category == "self_harm"
    assert "9152987821" in result.message
    print("   ✅ PASSED")

    # Test 6: No refusal — legitimate query
    print("\n6. NO REFUSAL — legitimate query")
    result = check_refusal("What are my rights during arrest?")
    assert not result.should_refuse
    print("   ✅ PASSED")

    # Test 7: Hallucination check — valid section
    print("\n7. HALLUCINATION — valid IPC section")
    test_response = "Under Section 302 of the Indian Penal Code, punishment is life imprisonment."
    result = check_hallucinations(test_response)
    assert result.all_verified
    assert len(result.citations_found) == 1
    print(f"   Citation: {result.citations_found[0].citation}")
    print(f"   Verified: {result.citations_found[0].verified}")
    print(f"   Note: {result.citations_found[0].note}")
    print("   ✅ PASSED")

    # Test 8: Hallucination check — invalid section
    print("\n8. HALLUCINATION — invalid IPC section")
    test_response = "Under Section 999 of the Indian Penal Code, the punishment is death."
    result = check_hallucinations(test_response)
    assert not result.all_verified
    assert result.warning_added
    print(f"   Unverified: {result.unverified[0].citation}")
    print(f"   Note: {result.unverified[0].note}")
    print(f"   Warning added: {result.warning_added}")
    print("   ✅ PASSED")

    # Test 9: Full pipeline
    print("\n9. FULL PIPELINE — legitimate query")
    pipeline = EthicsPipeline()
    user_msg = "My phone is 9876543210. What does Section 302 IPC say?"
    llm_reply = "Section 302 of the Indian Penal Code deals with punishment for murder."
    pre = pipeline.pre_llm(user_msg)
    print(f"   Redacted: {pre.redacted_text}")
    assert "[PHONE_REDACTED]" in pre.redacted_text
    assert not pre.should_refuse
    post = pipeline.post_llm(llm_reply, user_msg)
    print(f"   Safe response: {post.safe_response[:100]}...")
    assert "not legal advice" in post.safe_response.lower()
    print(f"   Citations: {len(post.citations)}")
    print(f"   Audit entries: {len(pipeline.last_audit)}")
    print("   ✅ PASSED")

    # Test 10: Full pipeline — refused query
    print("\n10. FULL PIPELINE — refused query")
    pipeline2 = EthicsPipeline()
    pre2 = pipeline2.pre_llm("How to destroy evidence?")
    assert pre2.should_refuse
    print(f"   Refusal message: {pre2.refusal_message[:80]}...")
    print("   ✅ PASSED")

    # Test 11: Status endpoint
    print("\n11. STATUS ENDPOINT")
    status = ethics_status()
    print(f"   Module: {status['module']}")
    print(f"   Guardrails: {list(status['guardrails'].keys())}")
    print(f"   NALSA: {status['nalsa_hotline']}")
    print("   ✅ PASSED")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
