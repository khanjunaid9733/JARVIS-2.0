---
name: gaming-tournament-bracket
description: Generate and manage esports tournament brackets.
---

# Tournament Bracket Generator Skill

## Purpose
Generate and manage esports tournament brackets.

## When to Activate
Activate when the user asks to:
- tournament bracket
- esports bracket
- round robin
- create tournament

## Core Workflows

Generate single/double elimination or round-robin bracket from player list.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
