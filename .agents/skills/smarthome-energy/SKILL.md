---
name: smarthome-energy
description: Track energy consumption of smart devices and appliances.
---

# Energy Monitor Skill

## Purpose
Track energy consumption of smart devices and appliances.

## When to Activate
Activate when the user asks to:
- energy usage
- power consumption
- electricity monitor

## Core Workflows

Query Home Assistant `sensor.energy_today` or Emporia Vue API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
