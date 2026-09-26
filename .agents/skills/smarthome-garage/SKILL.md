---
name: smarthome-garage
description: Open or close smart garage doors via MyQ or Home Assistant.
---

# Garage Door Control Skill

## Purpose
Open or close smart garage doors via MyQ or Home Assistant.

## When to Activate
Activate when the user asks to:
- open garage
- close garage door
- is garage open

## Core Workflows

POST to MyQ API or Home Assistant `cover.open_cover` service.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
