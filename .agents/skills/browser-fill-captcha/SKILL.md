---
name: browser-fill-captcha
description: Attempt to handle simple CAPTCHAs using 2captcha service.
---

# CAPTCHA Handler Skill

## Purpose
Attempt to handle simple CAPTCHAs using 2captcha service.

## When to Activate
Activate when the user asks to:
- solve CAPTCHA
- handle captcha
- bypass verification

## Core Workflows

Submit base64 image to 2captcha API, wait for solution, fill in response.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
