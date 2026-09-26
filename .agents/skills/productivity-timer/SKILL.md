---
name: productivity-timer
description: Start countdown timers or stopwatches and alert on completion.
---

# Timer / Stopwatch Skill

## Purpose
Start countdown timers or stopwatches and alert on completion.

## When to Activate
Activate when the user asks to:
- set timer for
- start stopwatch
- countdown <time>

## Core Workflows

Use threading.Timer or JARVIS scheduler for countdown, fire notification on completion.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
