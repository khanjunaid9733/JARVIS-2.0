---
name: food-wine-pair
description: Recommend wine pairings for any dish or cuisine.
---

# Wine Pairing Advisor Skill

## Purpose
Recommend wine pairings for any dish or cuisine.

## When to Activate
Activate when the user asks to:
- wine pairing
- what wine with
- wine for
- wine recommendation

## Core Workflows

Prompt: `Recommend 3 wines to pair with {dish}. Include: variety, region, flavor notes, and why it works.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
