---
name: web-weather
description: Get current weather and forecast for any city using Open-Meteo (no key).
---

# Weather Lookup Skill

## Purpose
Get current weather and forecast for any city using Open-Meteo (no key).

## When to Activate
Activate when the user asks to:
- what's the weather in
- weather forecast
- temperature in <city>

## Core Workflows

GET `https://api.open-meteo.com/v1/forecast?latitude=X&longitude=Y&current_weather=true`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
