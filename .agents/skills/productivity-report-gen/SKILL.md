---
name: productivity-report-gen
description: Auto-generate a weekly summary of activities, commits, and tasks.
---

# Weekly Report Generator Skill

## Purpose
Auto-generate a weekly summary of activities, commits, and tasks.

## When to Activate
Activate when the user asks to:
- weekly report
- week summary
- what did I do this week

## Core Workflows

Aggregate: git log (last 7d) + completed tasks + time tracking + calendar events.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
