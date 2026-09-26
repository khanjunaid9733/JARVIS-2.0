---
name: health-sleep-track
description: Log sleep times and quality, track weekly patterns.
---

# Sleep Tracker Skill

## Purpose
Log sleep times and quality, track weekly patterns.

## When to Activate
Activate when the user asks to:
- log sleep
- sleep last night
- sleep tracker
- I slept

## Core Workflows

Store bedtime/wake-time in JARVIS_HOME/health/sleep.csv. Compute duration and quality score.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
