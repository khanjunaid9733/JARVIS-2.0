---
name: smarthome-scene
description: Activate predefined scenes (Movie Mode, Sleep Mode, Away Mode).
---

# Smart Home Scene Skill

## Purpose
Activate predefined scenes (Movie Mode, Sleep Mode, Away Mode).

## When to Activate
Activate when the user asks to:
- activate scene
- movie mode
- sleep mode
- away mode

## Core Workflows

POST to `http://<HA_HOST>/api/services/scene/turn_on` with entity_id.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
