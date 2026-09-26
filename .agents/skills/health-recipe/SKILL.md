---
name: health-recipe
description: Find and generate healthy recipes based on ingredients or dietary restrictions.
---

# Healthy Recipe Finder Skill

## Purpose
Find and generate healthy recipes based on ingredients or dietary restrictions.

## When to Activate
Activate when the user asks to:
- recipe
- what can I cook with
- healthy meal
- recipe for

## Core Workflows

GET Spoonacular API `/recipes/findByIngredients` or prompt LLM with ingredient list.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
