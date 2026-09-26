---
name: legal-gdpr-check
description: Check code, APIs, and data practices for GDPR compliance.
---

# GDPR Compliance Checker Skill

## Purpose
Check code, APIs, and data practices for GDPR compliance.

## When to Activate
Activate when the user asks to:
- GDPR
- data privacy
- personal data
- compliance check

## Core Workflows

Check: lawful basis for processing, data minimization, consent mechanisms, breach notification, right to erasure.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
