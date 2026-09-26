---
name: smarthome-routine
description: Execute a sequence of smart home actions as a routine.
---

# Morning / Evening Routine Skill

## Purpose
Execute a sequence of smart home actions as a routine.

## When to Activate
Activate when the user asks to:
- morning routine
- good morning
- good night routine
- bedtime

## Core Workflows

Execute: lights on, thermostat set, news briefing, weather, calendar events.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
