---
name: productivity-goal-track
description: Set, track progress, and celebrate completion of personal goals.
---

# Goal Tracker Skill

## Purpose
Set, track progress, and celebrate completion of personal goals.

## When to Activate
Activate when the user asks to:
- set goal
- track goal
- goal progress
- mark goal complete

## Core Workflows

Store goals as YAML with progress %, due dates, and milestones in durable memory.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
