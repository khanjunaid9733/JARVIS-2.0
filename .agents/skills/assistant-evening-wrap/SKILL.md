---
name: assistant-evening-wrap
description: Summarize the day's accomplishments and prepare tomorrow's plan.
---

# Evening Wrap-Up Skill

## Purpose
Summarize the day's accomplishments and prepare tomorrow's plan.

## When to Activate
Activate when the user asks to:
- evening summary
- end of day
- wrap up day
- recap today

## Core Workflows

Aggregate: completed tasks + key events + outstanding work + tomorrow's schedule.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
