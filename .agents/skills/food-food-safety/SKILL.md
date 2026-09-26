---
name: food-food-safety
description: Provide food safety guidelines for storage, handling, and temperature.
---

# Food Safety Guide Skill

## Purpose
Provide food safety guidelines for storage, handling, and temperature.

## When to Activate
Activate when the user asks to:
- food safety
- how long does last
- safe temperature
- food storage

## Core Workflows

Prompt: `What are the food safety guidelines for {food}? Include storage temperature, shelf life, and handling.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
