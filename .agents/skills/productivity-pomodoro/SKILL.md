---
name: productivity-pomodoro
description: Run Pomodoro focus sessions with work and break intervals.
---

# Pomodoro Timer Skill

## Purpose
Run Pomodoro focus sessions with work and break intervals.

## When to Activate
Activate when the user asks to:
- start pomodoro
- focus session
- 25 minute focus
- pomodoro

## Core Workflows

25-minute work interval + 5-minute break, cycling 4 times then long break.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
