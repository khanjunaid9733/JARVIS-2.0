---
name: legal-statute-lookup
description: Look up specific statutes and legal codes.
---

# Statute & Law Lookup Skill

## Purpose
Look up specific statutes and legal codes.

## When to Activate
Activate when the user asks to:
- find law
- statute lookup
- legal code
- regulation text

## Core Workflows

Use eCFR API (US federal regulations) or Congress.gov API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
