---
name: web-whois
description: Query registration, expiry, and owner info for any domain.
---

# WHOIS Domain Lookup Skill

## Purpose
Query registration, expiry, and owner info for any domain.

## When to Activate
Activate when the user asks to:
- whois <domain>
- who owns <domain>
- domain info

## Core Workflows

Use `python-whois` library or `whois` CLI subprocess call.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
