---
name: food-bread-baking
description: Guide through bread baking with timing, hydration, and technique.
---

# Bread Baking Assistant Skill

## Purpose
Guide through bread baking with timing, hydration, and technique.

## When to Activate
Activate when the user asks to:
- bake bread
- bread recipe
- sourdough
- proofing time

## Core Workflows

Prompt: `Guide me through baking {bread_type}. Include: hydration ratio, timing, temperature, troubleshooting.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
