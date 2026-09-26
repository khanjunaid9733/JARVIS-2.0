---
name: productivity-standup
description: Auto-generate a standup report from recent git commits and tasks.
---

# Daily Standup Generator Skill

## Purpose
Auto-generate a standup report from recent git commits and tasks.

## When to Activate
Activate when the user asks to:
- generate standup
- daily report
- what did I do today
- standup notes

## Core Workflows

Aggregate: yesterday's git commits + completed tasks + planned todos.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
