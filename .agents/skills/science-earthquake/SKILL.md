---
name: science-earthquake
description: Get real-time and historical earthquake data from USGS.
---

# Earthquake Data Lookup Skill

## Purpose
Get real-time and historical earthquake data from USGS.

## When to Activate
Activate when the user asks to:
- earthquake
- seismic activity
- earthquake near
- recent earthquakes

## Core Workflows

GET `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
