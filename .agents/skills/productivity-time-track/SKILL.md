---
name: productivity-time-track
description: Track time spent on projects and activities.
---

# Time Tracker Skill

## Purpose
Track time spent on projects and activities.

## When to Activate
Activate when the user asks to:
- start tracking
- stop tracking
- time spent on
- log hours

## Core Workflows

Store start/stop timestamps in JARVIS_HOME/timetrack.jsonl, compute durations.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
