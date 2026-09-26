---
name: legal-background-check
description: Explain legal background check procedures and compliance.
---

# Background Check Guide Skill

## Purpose
Explain legal background check procedures and compliance.

## When to Activate
Activate when the user asks to:
- background check
- employment screening
- FCRA compliance
- criminal check

## Core Workflows

Prompt: `Explain legal requirements for background checks in {jurisdiction}. Include FCRA, ban-the-box, consent.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
