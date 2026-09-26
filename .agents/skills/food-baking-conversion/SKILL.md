---
name: food-baking-conversion
description: Convert cooking measurements between cups, grams, ounces, ml.
---

# Baking Measurement Converter Skill

## Purpose
Convert cooking measurements between cups, grams, ounces, ml.

## When to Activate
Activate when the user asks to:
- convert measurements
- cups to grams
- cooking conversion
- ml to oz

## Core Workflows

Use ingredient-specific density conversion tables for accurate weight conversions.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
