---
name: legal-terms-draft
description: Draft Terms of Service and Privacy Policy for web apps.
---

# Terms & Privacy Policy Skill

## Purpose
Draft Terms of Service and Privacy Policy for web apps.

## When to Activate
Activate when the user asks to:
- terms of service
- privacy policy
- legal pages
- ToS

## Core Workflows

Prompt: `Draft {document} for a {product_type} handling {data_types} targeting {jurisdiction}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
