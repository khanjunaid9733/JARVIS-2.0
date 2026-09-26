---
name: food-leftover-ideas
description: Suggest creative recipes using leftover ingredients.
---

# Leftover Meal Ideas Skill

## Purpose
Suggest creative recipes using leftover ingredients.

## When to Activate
Activate when the user asks to:
- leftovers
- use up
- what to do with
- transform leftovers

## Core Workflows

Prompt: `Suggest 5 creative recipes using these leftovers: {ingredients}. Minimize waste.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
