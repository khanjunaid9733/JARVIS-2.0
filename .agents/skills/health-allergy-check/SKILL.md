---
name: health-allergy-check
description: Check if a recipe or product contains known allergens.
---

# Allergy & Ingredient Checker Skill

## Purpose
Check if a recipe or product contains known allergens.

## When to Activate
Activate when the user asks to:
- allergen check
- contains gluten
- allergy safe
- ingredients allergens

## Core Workflows

Parse ingredient list against allergen database (FDA top 9 allergens).

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
