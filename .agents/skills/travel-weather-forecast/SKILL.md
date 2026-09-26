---
name: travel-weather-forecast
description: Get a 7-day weather forecast for any travel destination.
---

# Travel Weather Forecast Skill

## Purpose
Get a 7-day weather forecast for any travel destination.

## When to Activate
Activate when the user asks to:
- weather in <city>
- forecast for <destination>
- travel weather

## Core Workflows

GET Open-Meteo API with geocoding: lat/lon from city name → forecast JSON.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
