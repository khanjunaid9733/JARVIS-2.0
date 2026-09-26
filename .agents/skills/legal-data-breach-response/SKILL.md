---
name: legal-data-breach-response
description: Create a step-by-step data breach response protocol.
---

# Data Breach Response Plan Skill

## Purpose
Create a step-by-step data breach response protocol.

## When to Activate
Activate when the user asks to:
- data breach
- breach response
- incident response plan
- security incident

## Core Workflows

Steps: Identify → Contain → Assess → Notify (regulators, individuals) → Remediate → Review.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
