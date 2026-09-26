---
name: security-password-check
description: Evaluate password strength against NIST guidelines.
---

# Password Strength Checker Skill

## Purpose
Evaluate password strength against NIST guidelines.

## When to Activate
Activate when the user asks to:
- check password strength
- is this password strong
- rate my password

## Core Workflows

Check length >= 16, entropy >= 60 bits, no known breached patterns (HaveIBeenPwned API k-anonymity).

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
