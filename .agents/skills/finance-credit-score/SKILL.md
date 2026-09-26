---
name: finance-credit-score
description: Parse and display credit score report summaries.
---

# Credit Score Monitor Skill

## Purpose
Parse and display credit score report summaries.

## When to Activate
Activate when the user asks to:
- credit score
- check credit
- credit report

## Core Workflows

Parse annual credit report PDF or integrate with Credit Karma API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
