---
name: health-heart-rate
description: Display and log heart rate data from wearable devices.
---

# Heart Rate Monitor Skill

## Purpose
Display and log heart rate data from wearable devices.

## When to Activate
Activate when the user asks to:
- heart rate
- BPM
- pulse
- resting heart rate

## Core Workflows

Query Fitbit or Garmin API for current/resting/active heart rate data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
