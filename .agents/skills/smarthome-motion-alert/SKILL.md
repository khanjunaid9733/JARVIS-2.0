---
name: smarthome-motion-alert
description: Process motion detected events from smart sensors.
---

# Motion Alert Handler Skill

## Purpose
Process motion detected events from smart sensors.

## When to Activate
Activate when the user asks to:
- motion detected
- someone at door
- security alert

## Core Workflows

Subscribe to Home Assistant webhook trigger and emit `security.motion` event.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
