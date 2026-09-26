---
name: travel-timezone
description: Convert times between any two timezones for travel planning.
---

# Timezone Converter Skill

## Purpose
Convert times between any two timezones for travel planning.

## When to Activate
Activate when the user asks to:
- time in <city>
- timezone conversion
- what time is it in
- convert to timezone

## Core Workflows

Use `pytz` library: `datetime.now(pytz.timezone('America/New_York'))`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
