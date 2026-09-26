---
name: health-stretching
description: Generate targeted stretching routines for specific body areas.
---

# Stretching Routine Creator Skill

## Purpose
Generate targeted stretching routines for specific body areas.

## When to Activate
Activate when the user asks to:
- stretching routine
- stretch for
- flexibility exercises
- yoga stretches

## Core Workflows

Prompt: `Create a 10-minute stretching routine targeting {area} for {goal}. Include reps and duration.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
