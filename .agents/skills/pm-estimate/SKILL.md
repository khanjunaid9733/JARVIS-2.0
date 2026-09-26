---
name: pm-estimate
description: Estimate development effort using story points or T-shirt sizing.
---

# Effort Estimator Skill

## Purpose
Estimate development effort using story points or T-shirt sizing.

## When to Activate
Activate when the user asks to:
- estimate effort
- how long will it take
- story points
- effort estimate

## Core Workflows

Use Planning Poker technique via LLM: analyze complexity + uncertainty + risk.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
