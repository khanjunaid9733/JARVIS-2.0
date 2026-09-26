---
name: smarthome-lights
description: Turn on/off, dim, and change colors of smart lights via Home Assistant.
---

# Smart Light Controller Skill

## Purpose
Turn on/off, dim, and change colors of smart lights via Home Assistant.

## When to Activate
Activate when the user asks to:
- turn on lights
- dim lights
- set lights to red
- bedroom lights off

## Core Workflows

POST to `http://<HA_HOST>/api/services/light/turn_on` with entity_id and brightness.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
