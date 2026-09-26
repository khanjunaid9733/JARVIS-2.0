---
name: si-morning-routine
description: Design an optimized personal morning routine.
---

# Morning Routine Optimizer Skill

## Purpose
Design an optimized personal morning routine.

## When to Activate
Activate when the user asks to:
- morning routine
- optimize morning
- start day routine
- AM routine

## Core Workflows

Prompt: `Design a {duration}-minute morning routine for {goal}. Include: time slots, activities, rationale.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
