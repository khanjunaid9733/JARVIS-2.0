---
name: health-calorie-count
description: Estimate calories in meals from a description or food name.
---

# Calorie Counter Skill

## Purpose
Estimate calories in meals from a description or food name.

## When to Activate
Activate when the user asks to:
- calories in
- how many calories
- calorie count
- nutritional info

## Core Workflows

Use USDA FoodData Central API or prompt LLM for estimate.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
