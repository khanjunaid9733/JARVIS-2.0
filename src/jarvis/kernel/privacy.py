from __future__ import annotations

"""PII Seam & Data Privacy Policy (Milestone M2.5, spec §80.5 / §84.4 / §131.4).

Provides deterministic data classification, pattern-based PII detection,
in-place redaction, and fail-closed privacy gating for memory ingestion
and state projections.

Invariants:
1. Hermetic & Deterministic: No ambient clocks, no network calls, no model
   inference. Identical text + identical policy yields byte-identical
   sanitized output and identical evaluation outcomes.
2. Data-Not-Branches: Classification hierarchies, trust ranks, and PII
   taxonomies are declared as DATA constants, matching the §80.5 precedent.
3. Fail-Closed Privacy: Under CONFIDENTIAL or RESTRICTED classifications,
   unredacted sensitive credentials (API keys, private keys, passwords)
   cannot pass through unmasked when fail_closed is True.
4. Non-Leaking Audit: Audit events record detection counts and PII categories
   without ever including raw sensitive byte values in logs or event streams.
5. Strictly Additive: Does not alter existing frozen modules (1-17, M2.1-M2.4).
"""

import enum
import re
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Data Classification Hierarchy (§80.5 / §131.4)
# ---------------------------------------------------------------------------

class DataClassification(str, enum.Enum):
    """Declared data classification levels.

    Compatible with `policy.py`'s `PrivacyClass` string literals:
    PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


CLASSIFICATION_RANK: Mapping[DataClassification, int] = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.CONFIDENTIAL: 2,
    DataClassification.RESTRICTED: 3,
}


# ---------------------------------------------------------------------------
# PII Taxonomy & Detection Datums
# ---------------------------------------------------------------------------

class PIIType(str, enum.Enum):
    """Categories of sensitive / personally identifiable information."""

    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    PRIVATE_KEY = "private_key"
    PASSWORD = "password"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"


class PIIDetection(BaseModel):
    """A detected PII occurrence with exact span boundaries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pii_type: PIIType
    start: int
    end: int
    matched_text: str
    mask: str


# ---------------------------------------------------------------------------
# Redaction Patterns (High-Precision Deterministic Matchers)
# ---------------------------------------------------------------------------

# Precompiled regex patterns for standard PII & secret signatures
_PATTERNS: list[tuple[PIIType, re.Pattern[str], str]] = [
    # 1. Private keys
    (
        PIIType.PRIVATE_KEY,
        re.compile(
            r"-----BEGIN\s+(?:[A-Z\s]+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:[A-Z\s]+)?PRIVATE\s+KEY-----",
            re.MULTILINE,
        ),
        "[REDACTED:PRIVATE_KEY]",
    ),
    # 2. Known provider API keys & tokens
    (
        PIIType.API_KEY,
        re.compile(
            r"\b(?:sk-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16})\b"
        ),
        "[REDACTED:API_KEY]",
    ),
    # 3. Bearer tokens
    (
        PIIType.BEARER_TOKEN,
        re.compile(
            r"(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{20,})\b"
        ),
        "Bearer [REDACTED:BEARER_TOKEN]",
    ),
    # 4. Explicit key-value secrets / passwords
    (
        PIIType.PASSWORD,
        re.compile(
            r"(?i)(?:password|passwd|secret|api_key|token)\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?"
        ),
        "[REDACTED:PASSWORD]",
    ),
    # 5. Social Security Numbers (SSN)
    (
        PIIType.SSN,
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[REDACTED:SSN]",
    ),
    # 6. Credit Card Numbers (13-19 digits with optional hyphens/spaces)
    (
        PIIType.CREDIT_CARD,
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b"),
        "[REDACTED:CREDIT_CARD]",
    ),
    # 7. Email addresses
    (
        PIIType.EMAIL,
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED:EMAIL]",
    ),
    # 8. Phone numbers (US/international formats)
    (
        PIIType.PHONE,
        re.compile(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "[REDACTED:PHONE]",
    ),
    # 9. IP Addresses (IPv4)
    (
        PIIType.IP_ADDRESS,
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        ),
        "[REDACTED:IP_ADDRESS]",
    ),
]


# ---------------------------------------------------------------------------
# Redactor Engine
# ---------------------------------------------------------------------------

class PIIRedactor:
    """Deterministic PII scanner and redaction engine.

    Scans text for declared PII signatures and performs non-overlapping,
    deterministic masking.
    """

    @classmethod
    def scan(cls, text: str) -> list[PIIDetection]:
        """Scans text and returns all detected PII occurrences sorted by span."""
        if not text:
            return []

        detections: list[PIIDetection] = []
        for pii_type, pattern, mask in _PATTERNS:
            for match in pattern.finditer(text):
                # For patterns with capture groups (e.g. Bearer, password=),
                # locate the sensitive group if present
                if match.groups():
                    start, end = match.start(1), match.end(1)
                    matched_val = match.group(1)
                    # If mask is full match replacement vs group replacement
                    applied_mask = mask if not mask.startswith("Bearer ") else "[REDACTED:BEARER_TOKEN]"
                else:
                    start, end = match.start(), match.end()
                    matched_val = match.group(0)
                    applied_mask = mask

                detections.append(
                    PIIDetection(
                        pii_type=pii_type,
                        start=start,
                        end=end,
                        matched_text=matched_val,
                        mask=applied_mask,
                    )
                )

        # Sort by start index; for overlapping matches, longest match takes precedence
        detections.sort(key=lambda d: (d.start, -(d.end - d.start)))

        # Filter out overlaps deterministically
        non_overlapping: list[PIIDetection] = []
        last_end = -1
        for det in detections:
            if det.start >= last_end:
                non_overlapping.append(det)
                last_end = det.end

        return non_overlapping

    @classmethod
    def redact(cls, text: str, detections: Sequence[PIIDetection] | None = None) -> str:
        """Applies masks to all non-overlapping detections in reverse order."""
        if not text:
            return text

        active_detections = list(detections if detections is not None else cls.scan(text))
        if not active_detections:
            return text

        # Replace from end to start to preserve character indices
        active_detections.sort(key=lambda d: d.start, reverse=True)
        chars = list(text)
        for det in active_detections:
            chars[det.start:det.end] = list(det.mask)

        return "".join(chars)


# ---------------------------------------------------------------------------
# Privacy Policy & Evaluation Datums
# ---------------------------------------------------------------------------

class PrivacyPolicy(BaseModel):
    """Frozen policy declaring privacy rules and enforcement constraints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    classification: DataClassification = DataClassification.INTERNAL
    fail_closed: bool = True
    auto_redact: bool = True
    allowed_pii: frozenset[PIIType] = Field(default_factory=frozenset)


class PrivacyEvaluation(BaseModel):
    """Outcome of evaluating content against a PrivacyPolicy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    classification: DataClassification
    sanitized_content: str
    detections: tuple[PIIDetection, ...]
    reason: str


# ---------------------------------------------------------------------------
# Privacy Gate & Sanitizer Seam
# ---------------------------------------------------------------------------

class PrivacySanitizer:
    """Deterministic privacy gate and sanitization seam for memory writers.

    Pure valuation: identical content + identical policy -> identical evaluation.
    """

    def __init__(self, policy: PrivacyPolicy | None = None) -> None:
        self._policy = policy or PrivacyPolicy()

    @property
    def policy(self) -> PrivacyPolicy:
        return self._policy

    def evaluate(
        self,
        content: str,
        *,
        classification: DataClassification | None = None,
    ) -> PrivacyEvaluation:
        """Evaluates content against policy and produces sanitized text."""
        effective_classification = classification or self._policy.classification
        detections = tuple(PIIRedactor.scan(content))

        # Check for disallowed PII
        disallowed = [
            d for d in detections if d.pii_type not in self._policy.allowed_pii
        ]

        if not disallowed:
            return PrivacyEvaluation(
                passed=True,
                classification=effective_classification,
                sanitized_content=content,
                detections=detections,
                reason="No disallowed PII detected",
            )

        # Disallowed PII is present
        sanitized = (
            PIIRedactor.redact(content, disallowed)
            if self._policy.auto_redact
            else content
        )

        # In fail-closed mode:
        # If classification is CONFIDENTIAL or RESTRICTED, or auto_redact is disabled,
        # fail the check unless auto-redacted and allowed
        is_sensitive = CLASSIFICATION_RANK[effective_classification] >= CLASSIFICATION_RANK[DataClassification.CONFIDENTIAL]

        if self._policy.fail_closed and is_sensitive and not self._policy.auto_redact:
            types_found = sorted({d.pii_type.value for d in disallowed})
            return PrivacyEvaluation(
                passed=False,
                classification=effective_classification,
                sanitized_content=content,
                detections=detections,
                reason=f"Unredacted sensitive PII ({', '.join(types_found)}) prohibited under {effective_classification.value}",
            )

        types_found = sorted({d.pii_type.value for d in disallowed})
        return PrivacyEvaluation(
            passed=True,
            classification=effective_classification,
            sanitized_content=sanitized,
            detections=detections,
            reason=f"Sanitized {len(disallowed)} PII occurrences ({', '.join(types_found)})",
        )

    def audit_event(self, evaluation: PrivacyEvaluation) -> dict[str, Any]:
        """Generates an audit payload without leaking sensitive byte content."""
        counts: dict[str, int] = {}
        for d in evaluation.detections:
            counts[d.pii_type.value] = counts.get(d.pii_type.value, 0) + 1

        return {
            "classification": evaluation.classification.value,
            "passed": evaluation.passed,
            "total_detections": len(evaluation.detections),
            "pii_counts": counts,
            "reason": evaluation.reason,
        }


__all__ = [
    "CLASSIFICATION_RANK",
    "DataClassification",
    "PIIDetection",
    "PIIRedactor",
    "PIIType",
    "PrivacyEvaluation",
    "PrivacyPolicy",
    "PrivacySanitizer",
]
