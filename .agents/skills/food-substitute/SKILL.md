---
name: food-substitute
description: Find substitutes for any cooking ingredient.
---

# Ingredient Substituter Skill

## Purpose
Find substitutes for any cooking ingredient.

## When to Activate
Activate when the user asks to:
- substitute for
- replacement for
- I don't have
- what can I use instead

## Core Workflows

Prompt: `What are the best substitutes for {ingredient} in {dish}? Explain ratios and flavor differences.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
