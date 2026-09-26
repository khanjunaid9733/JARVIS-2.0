---
name: security-breach-check
description: Check if an email has been exposed in known data breaches via HaveIBeenPwned.
---

# Breach Checker Skill

## Purpose
Check if an email has been exposed in known data breaches via HaveIBeenPwned.

## When to Activate
Activate when the user asks to:
- check for breach
- has my email been hacked
- breached passwords

## Core Workflows

GET `https://haveibeenpwned.com/api/v3/breachedaccount/<email>` with API key.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
