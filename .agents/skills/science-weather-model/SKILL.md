---
name: science-weather-model
description: Fetch detailed meteorological data (pressure, humidity, wind).
---

# Meteorology Data Skill

## Purpose
Fetch detailed meteorological data (pressure, humidity, wind).

## When to Activate
Activate when the user asks to:
- atmospheric pressure
- wind speed
- humidity data
- meteorology

## Core Workflows

GET Open-Meteo API with hourly parameters for detailed atmospheric data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
