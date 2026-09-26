---
name: food-shopping-list
description: Generate an optimized grocery shopping list from a meal plan.
---

# Smart Shopping List Skill

## Purpose
Generate an optimized grocery shopping list from a meal plan.

## When to Activate
Activate when the user asks to:
- shopping list
- grocery list
- what to buy
- ingredients needed

## Core Workflows

Aggregate ingredients across all recipes, group by category, optimize quantities.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
