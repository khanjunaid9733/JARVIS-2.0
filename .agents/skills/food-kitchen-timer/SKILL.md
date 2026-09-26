---
name: food-kitchen-timer
description: Manage multiple simultaneous cooking timers for a meal.
---

# Multi-Stage Cooking Timer Skill

## Purpose
Manage multiple simultaneous cooking timers for a meal.

## When to Activate
Activate when the user asks to:
- cooking timer
- time this
- set kitchen timer
- multi timer

## Core Workflows

Track multiple named timers in parallel, alert when each completes.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
