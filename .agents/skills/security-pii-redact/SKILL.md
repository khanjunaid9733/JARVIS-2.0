---
name: security-pii-redact
description: Scan and redact personally identifiable information from text or files.
---

# PII Redactor Skill

## Purpose
Scan and redact personally identifiable information from text or files.

## When to Activate
Activate when the user asks to:
- redact PII
- remove personal info
- anonymize data

## Core Workflows

Use spaCy NER or regex patterns to detect and mask names, emails, phones, SSNs.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
