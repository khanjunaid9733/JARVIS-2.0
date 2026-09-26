---
name: food-coffee-guide
description: Guide optimal coffee brewing for any method.
---

# Coffee Brewing Guide Skill

## Purpose
Guide optimal coffee brewing for any method.

## When to Activate
Activate when the user asks to:
- coffee brewing
- how to brew
- coffee ratio
- pour over
- espresso

## Core Workflows

Prompt: `Explain optimal brewing parameters for {method}: grind size, ratio, temperature, time, technique.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
