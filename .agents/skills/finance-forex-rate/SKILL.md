---
name: finance-forex-rate
description: Get live currency exchange rates between any pair.
---

# Forex Exchange Rate Skill

## Purpose
Get live currency exchange rates between any pair.

## When to Activate
Activate when the user asks to:
- exchange rate
- convert currency
- USD to EUR rate

## Core Workflows

GET `https://open.er-api.com/v6/latest/<BASE>` for live rates.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
