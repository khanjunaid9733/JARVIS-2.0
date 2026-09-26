---
name: smarthome-weather-station
description: Read temperature, humidity, CO2, and air quality from local sensors.
---

# Home Weather Station Skill

## Purpose
Read temperature, humidity, CO2, and air quality from local sensors.

## When to Activate
Activate when the user asks to:
- indoor temperature
- humidity level
- air quality
- CO2 level

## Core Workflows

Query local MQTT broker or Home Assistant sensor entities.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
