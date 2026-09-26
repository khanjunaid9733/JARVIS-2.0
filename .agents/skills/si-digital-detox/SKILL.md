---
name: si-digital-detox
description: Plan a meaningful break from digital devices.
---

# Digital Detox Planner Skill

## Purpose
Plan a meaningful break from digital devices.

## When to Activate
Activate when the user asks to:
- digital detox
- phone break
- screen time
- social media break

## Core Workflows

Prompt: `Create a {duration} digital detox plan. Include: what to remove, replacement activities, check-in protocol.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
