---
name: travel-cost-estimator
description: Estimate total trip cost including flights, hotels, food, and activities.
---

# Trip Cost Estimator Skill

## Purpose
Estimate total trip cost including flights, hotels, food, and activities.

## When to Activate
Activate when the user asks to:
- how much does trip cost
- trip budget
- estimate travel budget

## Core Workflows

Aggregate: flight avg + hotel_per_night × days + daily_food_budget × days + activities.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
