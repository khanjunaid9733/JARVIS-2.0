---
name: security-https-enforce
description: Verify all outbound API calls use HTTPS and reject HTTP.
---

# HTTPS Enforcer Skill

## Purpose
Verify all outbound API calls use HTTPS and reject HTTP.

## When to Activate
Activate when the user asks to:
- enforce HTTPS
- check TLS
- all calls HTTPS

## Core Workflows

Pre-flight check: assert url.startswith('https://') before any outbound request.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
