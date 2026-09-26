---
name: food-diet-advice
description: Provide general dietary advice for specific health goals.
---

# Diet & Nutrition Advisor Skill

## Purpose
Provide general dietary advice for specific health goals.

## When to Activate
Activate when the user asks to:
- diet advice
- what should I eat
- nutrition for
- diet plan for condition

## Core Workflows

Prompt: `Provide evidence-based dietary recommendations for {goal/condition}. Note: not medical advice.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
