---
name: science-space-iss
description: Get the current position of the International Space Station.
---

# ISS Tracker Skill

## Purpose
Get the current position of the International Space Station.

## When to Activate
Activate when the user asks to:
- ISS location
- space station
- where is ISS
- International Space Station

## Core Workflows

GET `http://api.open-notify.org/iss-now.json` for real-time ISS lat/lon.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
