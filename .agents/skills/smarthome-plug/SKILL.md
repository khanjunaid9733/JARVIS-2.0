---
name: smarthome-plug
description: Turn smart plugs on or off to control connected devices.
---

# Smart Plug Control Skill

## Purpose
Turn smart plugs on or off to control connected devices.

## When to Activate
Activate when the user asks to:
- turn on plug
- power off device
- smart switch

## Core Workflows

POST to Home Assistant `switch.turn_on` / `switch.turn_off` service.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
