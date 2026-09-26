---
name: gaming-tier-list
description: Create and analyze character/item tier lists for any game.
---

# Tier List Creator Skill

## Purpose
Create and analyze character/item tier lists for any game.

## When to Activate
Activate when the user asks to:
- tier list
- best characters
- ranking in game
- meta analysis

## Core Workflows

Prompt: `Create a tier list (S/A/B/C/D) for {game} characters/items based on current meta. Explain each placement.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
