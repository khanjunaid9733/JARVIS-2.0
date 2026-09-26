---
name: food-meal-plan
description: Create a 7-day meal plan with shopping list.
---

# Weekly Meal Planner Skill

## Purpose
Create a 7-day meal plan with shopping list.

## When to Activate
Activate when the user asks to:
- meal plan for the week
- weekly menu
- diet meal plan
- plan meals

## Core Workflows

Generate 3 meals/day × 7 days based on preferences. Compile ingredient shopping list.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
