---
name: health-bmi-calc
description: Calculate BMI and provide healthy weight range guidance.
---

# BMI Calculator Skill

## Purpose
Calculate BMI and provide healthy weight range guidance.

## When to Activate
Activate when the user asks to:
- BMI
- body mass index
- healthy weight
- am I overweight

## Core Workflows

BMI = weight_kg / height_m². Classify: <18.5 underweight, 18.5-25 normal, 25-30 overweight, >30 obese.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
