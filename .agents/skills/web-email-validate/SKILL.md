---
name: web-email-validate
description: Check if an email address is valid and deliverable via MX lookup.
---

# Email Validator Skill

## Purpose
Check if an email address is valid and deliverable via MX lookup.

## When to Activate
Activate when the user asks to:
- is <email> valid
- validate email address
- check email MX

## Core Workflows

Use DNS MX record lookup + SMTP handshake probe.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
