---
name: travel-emergency-contacts
description: Provide local emergency numbers for any country.
---

# Travel Emergency Contacts Skill

## Purpose
Provide local emergency numbers for any country.

## When to Activate
Activate when the user asks to:
- emergency number in
- police in <country>
- ambulance number
- travel emergency

## Core Workflows

Return country-specific emergency numbers: police, ambulance, fire, embassy.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
