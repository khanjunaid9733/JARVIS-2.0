---
name: legal-disclaimer-gen
description: Generate appropriate disclaimers for websites, products, or services.
---

# Legal Disclaimer Generator Skill

## Purpose
Generate appropriate disclaimers for websites, products, or services.

## When to Activate
Activate when the user asks to:
- legal disclaimer
- add disclaimer
- liability disclaimer
- medical disclaimer

## Core Workflows

Prompt: `Write a {type} disclaimer for a {business_type}. Cover appropriate limitations and protections.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
