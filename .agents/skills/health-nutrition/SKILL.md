---
name: health-nutrition
description: Generate meal plans and calculate macros/calories.
---

# Meal Plan & Nutrition Skill

## Purpose
Generate meal plans and calculate macros/calories.

## When to Activate
Activate when the user asks to:
- meal plan
- nutrition plan
- diet plan
- calorie intake
- macros

## Core Workflows

Prompt: `Create a {days}-day {diet_type} meal plan for {calories} calories/day. Include macros per meal.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
