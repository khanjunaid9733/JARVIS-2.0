---
name: health-nutrition-label
description: Parse and explain food nutrition labels.
---

# Nutrition Label Parser Skill

## Purpose
Parse and explain food nutrition labels.

## When to Activate
Activate when the user asks to:
- nutrition label
- what's in this food
- understand nutrition facts

## Core Workflows

Parse label values, explain % daily values, flag high sodium/sugar/fat.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
