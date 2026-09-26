---
name: web-currency-convert
description: Convert between any currencies using live exchange rates.
---

# Currency Converter Skill

## Purpose
Convert between any currencies using live exchange rates.

## When to Activate
Activate when the user asks to:
- convert USD to EUR
- how much is X dollars in rupees

## Core Workflows

GET `https://api.exchangerate-api.com/v4/latest/<BASE>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
