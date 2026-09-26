---
name: smarthome-irrigation
description: Schedule and manually trigger garden irrigation zones.
---

# Irrigation Controller Skill

## Purpose
Schedule and manually trigger garden irrigation zones.

## When to Activate
Activate when the user asks to:
- water garden
- irrigation zone on
- start sprinklers

## Core Workflows

POST to Home Assistant `switch.turn_on` for irrigation zone entities.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
