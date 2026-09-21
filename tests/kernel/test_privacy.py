from __future__ import annotations

"""Unit & Invariant Tests for Milestone M2.5: PII Seam & Data Privacy Policy."""

import pytest

from jarvis.kernel.privacy import (
    CLASSIFICATION_RANK,
    DataClassification,
    PIIDetection,
    PIIRedactor,
    PIIType,
    PrivacyEvaluation,
    PrivacyPolicy,
    PrivacySanitizer,
)


# ---------------------------------------------------------------------------
# 1. Classification Hierarchy & Ordering
# ---------------------------------------------------------------------------

def test_data_classification_hierarchy():
    """Classification rank strictly adheres to PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED."""
    assert CLASSIFICATION_RANK[DataClassification.PUBLIC] == 0
    assert CLASSIFICATION_RANK[DataClassification.INTERNAL] == 1
    assert CLASSIFICATION_RANK[DataClassification.CONFIDENTIAL] == 2
    assert CLASSIFICATION_RANK[DataClassification.RESTRICTED] == 3

    assert (
        CLASSIFICATION_RANK[DataClassification.PUBLIC]
        < CLASSIFICATION_RANK[DataClassification.INTERNAL]
        < CLASSIFICATION_RANK[DataClassification.CONFIDENTIAL]
        < CLASSIFICATION_RANK[DataClassification.RESTRICTED]
    )


# ---------------------------------------------------------------------------
# 2. PII Pattern Detection
# ---------------------------------------------------------------------------

def test_detect_api_keys():
    text = (
        "Here is OpenAI key sk-abcdef1234567890abcdef1234567890 "
        "and GitHub ghp_123456789012345678901234567890123456 "
        "and AWS AKIAIOSFODNN7EXAMPLE."
    )
    detections = PIIRedactor.scan(text)
    api_keys = [d for d in detections if d.pii_type == PIIType.API_KEY]
    assert len(api_keys) == 3
    assert api_keys[0].matched_text == "sk-abcdef1234567890abcdef1234567890"
    assert api_keys[1].matched_text == "ghp_123456789012345678901234567890123456"
    assert api_keys[2].matched_text == "AKIAIOSFODNN7EXAMPLE"


def test_detect_private_keys():
    text = (
        "Config file containing:\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y123456789...\n"
        "-----END RSA PRIVATE KEY-----\n"
        "End of config."
    )
    detections = PIIRedactor.scan(text)
    assert len(detections) == 1
    assert detections[0].pii_type == PIIType.PRIVATE_KEY
    assert "BEGIN RSA PRIVATE KEY" in detections[0].matched_text


def test_detect_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID"
    detections = PIIRedactor.scan(text)
    assert len(detections) == 1
    assert detections[0].pii_type == PIIType.BEARER_TOKEN
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID" in detections[0].matched_text


def test_detect_passwords_and_secrets():
    text = 'Connect using password="superSecretPassword123" or api_key: "topSecretToken999"'
    detections = PIIRedactor.scan(text)
    pw_detections = [d for d in detections if d.pii_type == PIIType.PASSWORD]
    assert len(pw_detections) == 2
    assert "superSecretPassword123" in [d.matched_text for d in pw_detections]
    assert "topSecretToken999" in [d.matched_text for d in pw_detections]


def test_detect_ssn():
    text = "User SSN is 123-45-6789 and another one is 987-65-4321."
    detections = PIIRedactor.scan(text)
    ssns = [d for d in detections if d.pii_type == PIIType.SSN]
    assert len(ssns) == 2
    assert ssns[0].matched_text == "123-45-6789"
    assert ssns[1].matched_text == "987-65-4321"


def test_detect_credit_card():
    text = "Card 4111-2222-3333-4444 was charged $50."
    detections = PIIRedactor.scan(text)
    cards = [d for d in detections if d.pii_type == PIIType.CREDIT_CARD]
    assert len(cards) == 1
    assert cards[0].matched_text == "4111-2222-3333-4444"


def test_detect_email():
    text = "Contact alice@example.com or bob.smith+dev@sub.domain.org for help."
    detections = PIIRedactor.scan(text)
    emails = [d for d in detections if d.pii_type == PIIType.EMAIL]
    assert len(emails) == 2
    assert emails[0].matched_text == "alice@example.com"
    assert emails[1].matched_text == "bob.smith+dev@sub.domain.org"


def test_detect_phone():
    text = "Call +1 (555) 123-4567 or 555-987-6543 today."
    detections = PIIRedactor.scan(text)
    phones = [d for d in detections if d.pii_type == PIIType.PHONE]
    assert len(phones) >= 2


def test_detect_ip_address():
    text = "Server running at 192.168.1.100 and external 10.0.0.1."
    detections = PIIRedactor.scan(text)
    ips = [d for d in detections if d.pii_type == PIIType.IP_ADDRESS]
    assert len(ips) == 2
    assert ips[0].matched_text == "192.168.1.100"
    assert ips[1].matched_text == "10.0.0.1"


# ---------------------------------------------------------------------------
# 3. Deterministic Redaction & Text Stability
# ---------------------------------------------------------------------------

def test_redact_multiple_pii_in_text():
    text = (
        "User alice@example.com with phone 555-123-4567 logged in from 192.168.1.1 "
        "using token sk-123456789012345678901234567890."
    )
    redacted = PIIRedactor.redact(text)

    assert "alice@example.com" not in redacted
    assert "555-123-4567" not in redacted
    assert "192.168.1.1" not in redacted
    assert "sk-123456789012345678901234567890" not in redacted

    assert "[REDACTED:EMAIL]" in redacted
    assert "[REDACTED:PHONE]" in redacted
    assert "[REDACTED:IP_ADDRESS]" in redacted
    assert "[REDACTED:API_KEY]" in redacted
    assert redacted.startswith("User [REDACTED:EMAIL]")


def test_redaction_empty_or_clean_text():
    assert PIIRedactor.redact("") == ""
    clean = "This is a clean sentence with no personal data."
    assert PIIRedactor.redact(clean) == clean


# ---------------------------------------------------------------------------
# 4. Privacy Policy & Fail-Closed Gate
# ---------------------------------------------------------------------------

def test_sanitizer_passes_clean_content():
    sanitizer = PrivacySanitizer()
    eval_result = sanitizer.evaluate("Clean operational log: job finished successfully.")
    assert eval_result.passed is True
    assert len(eval_result.detections) == 0
    assert eval_result.sanitized_content == "Clean operational log: job finished successfully."


def test_sanitizer_auto_redacts_by_default():
    sanitizer = PrivacySanitizer()
    content = "Sensitive contact: admin@company.internal."
    eval_result = sanitizer.evaluate(content)

    assert eval_result.passed is True
    assert len(eval_result.detections) == 1
    assert eval_result.sanitized_content == "Sensitive contact: [REDACTED:EMAIL]."


def test_sanitizer_fail_closed_on_confidential_when_auto_redact_false():
    policy = PrivacyPolicy(
        classification=DataClassification.CONFIDENTIAL,
        fail_closed=True,
        auto_redact=False,
    )
    sanitizer = PrivacySanitizer(policy)
    content = "Internal credential sk-abcdef1234567890abcdef1234567890"
    eval_result = sanitizer.evaluate(content)

    assert eval_result.passed is False
    assert "Unredacted sensitive PII" in eval_result.reason
    assert "api_key" in eval_result.reason


def test_sanitizer_allowed_pii_bypass():
    # If IP_ADDRESS is explicitly allowed in policy, it is neither redacted nor blocked
    policy = PrivacyPolicy(
        classification=DataClassification.CONFIDENTIAL,
        allowed_pii=frozenset([PIIType.IP_ADDRESS]),
        auto_redact=True,
    )
    sanitizer = PrivacySanitizer(policy)
    content = "Node connected at 192.168.1.50 with key sk-abcdef1234567890abcdef1234567890"
    eval_result = sanitizer.evaluate(content)

    assert eval_result.passed is True
    assert "192.168.1.50" in eval_result.sanitized_content
    assert "sk-abcdef1234567890abcdef1234567890" not in eval_result.sanitized_content
    assert "[REDACTED:API_KEY]" in eval_result.sanitized_content


# ---------------------------------------------------------------------------
# 5. Non-Leaking Audit Events
# ---------------------------------------------------------------------------

def test_audit_event_does_not_leak_raw_pii():
    sanitizer = PrivacySanitizer()
    raw_secret = "sk-live-secret-key-12345678901234567890"
    raw_email = "super_secret_user@private.corp"
    content = f"Auth credentials: {raw_secret} user {raw_email}"

    eval_result = sanitizer.evaluate(content)
    audit = sanitizer.audit_event(eval_result)

    audit_str = str(audit)
    assert raw_secret not in audit_str
    assert raw_email not in audit_str
    assert audit["total_detections"] == 2
    assert audit["pii_counts"]["api_key"] == 1
    assert audit["pii_counts"]["email"] == 1
    assert audit["passed"] is True


# ---------------------------------------------------------------------------
# 6. Determinism & Fold Stability
# ---------------------------------------------------------------------------

def test_evaluation_is_strictly_deterministic():
    sanitizer = PrivacySanitizer()
    text = "Call 555-123-4567 or email test@example.com."

    res1 = sanitizer.evaluate(text)
    res2 = sanitizer.evaluate(text)

    assert res1.sanitized_content == res2.sanitized_content
    assert len(res1.detections) == len(res2.detections)
    assert res1 == res2
