---
name: smarthome-fan
description: Control smart fan speed and oscillation.
---

# Smart Fan Control Skill

## Purpose
Control smart fan speed and oscillation.

## When to Activate
Activate when the user asks to:
- turn fan on
- fan speed
- oscillate fan
- fan timer

## Core Workflows

POST to Home Assistant `fan.set_percentage` with speed value 0-100.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
