---
name: food-nutrition-analyze
description: Calculate full nutrition facts for any recipe.
---

# Recipe Nutrition Analyzer Skill

## Purpose
Calculate full nutrition facts for any recipe.

## When to Activate
Activate when the user asks to:
- nutrition in recipe
- calories in
- macros for recipe
- nutritional value

## Core Workflows

Use Spoonacular recipe nutrition endpoint or USDA FoodData Central API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
