---
name: smarthome-thermostat
description: Set and read smart thermostat temperature and mode.
---

# Thermostat Control Skill

## Purpose
Set and read smart thermostat temperature and mode.

## When to Activate
Activate when the user asks to:
- set temperature to
- thermostat to
- heat to <temp>
- cool to

## Core Workflows

POST to `http://<HA_HOST>/api/services/climate/set_temperature`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
