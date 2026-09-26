---
name: travel-airport-info
description: Look up airport codes, terminal maps, and real-time flight status.
---

# Airport Information Skill

## Purpose
Look up airport codes, terminal maps, and real-time flight status.

## When to Activate
Activate when the user asks to:
- airport code
- flight status
- terminal info
- is flight <number> on time

## Core Workflows

Use AviationStack API or FlightAware for real-time flight data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
