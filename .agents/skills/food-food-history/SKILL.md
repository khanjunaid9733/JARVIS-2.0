---
name: food-food-history
description: Explore the history and cultural significance of foods.
---

# Food History & Culture Skill

## Purpose
Explore the history and cultural significance of foods.

## When to Activate
Activate when the user asks to:
- history of
- origin of food
- food culture
- where did come from

## Core Workflows

Prompt: `Explain the cultural history and origin of {food/dish}. Include regional variations and symbolism.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
