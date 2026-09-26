---
name: travel-safety-info
description: Provide safety tips and risk assessment for travel destinations.
---

# Travel Safety Advisor Skill

## Purpose
Provide safety tips and risk assessment for travel destinations.

## When to Activate
Activate when the user asks to:
- is <country> safe
- travel safety
- safety tips for

## Core Workflows

Prompt: `Provide safety tips for traveling to {destination}: risk level, areas to avoid, common scams, emergency contacts.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
