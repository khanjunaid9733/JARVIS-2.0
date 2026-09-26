---
name: si-negotiation
description: Teach negotiation strategies and tactics.
---

# Negotiation Coach Skill

## Purpose
Teach negotiation strategies and tactics.

## When to Activate
Activate when the user asks to:
- negotiate
- negotiation tips
- how to negotiate
- salary negotiation

## Core Workflows

Prompt: `Coach me on negotiating {situation}. Strategies: BATNA, anchoring, mirroring, concession framing.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
