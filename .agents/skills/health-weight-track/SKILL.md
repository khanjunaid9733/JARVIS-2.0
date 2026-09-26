---
name: health-weight-track
description: Log weight measurements and visualize progress trends.
---

# Weight Tracker Skill

## Purpose
Log weight measurements and visualize progress trends.

## When to Activate
Activate when the user asks to:
- log weight
- weight tracker
- how much do I weigh
- weight progress

## Core Workflows

Append date + weight to JARVIS_HOME/health/weight.csv. Plot weekly trend.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
