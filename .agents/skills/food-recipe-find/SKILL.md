---
name: food-recipe-find
description: Find recipes by ingredients, cuisine type, or dietary restrictions.
---

# Recipe Finder Skill

## Purpose
Find recipes by ingredients, cuisine type, or dietary restrictions.

## When to Activate
Activate when the user asks to:
- recipe with
- what can I make with
- recipe for
- vegan recipe
- keto recipe

## Core Workflows

GET Spoonacular API `/recipes/findByIngredients?ingredients=<list>`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
