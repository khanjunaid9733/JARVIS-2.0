---
name: science-climate
description: Retrieve historical climate data and CO2 levels.
---

# Climate Data Fetcher Skill

## Purpose
Retrieve historical climate data and CO2 levels.

## When to Activate
Activate when the user asks to:
- climate data
- temperature history
- CO2 levels
- global warming data

## Core Workflows

GET NOAA or NASA GISS Surface Temperature API for historical climate records.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
