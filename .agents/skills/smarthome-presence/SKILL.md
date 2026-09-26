---
name: smarthome-presence
description: Detect when home occupants arrive or depart using device tracking.
---

# Presence Detection Skill

## Purpose
Detect when home occupants arrive or depart using device tracking.

## When to Activate
Activate when the user asks to:
- is anyone home
- who's home
- track presence
- I'm home

## Core Workflows

Use Home Assistant `device_tracker` entities or UniFi controller API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
