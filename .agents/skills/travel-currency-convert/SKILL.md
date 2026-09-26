---
name: travel-currency-convert
description: Convert trip budget between local and destination currency.
---

# Travel Currency Converter Skill

## Purpose
Convert trip budget between local and destination currency.

## When to Activate
Activate when the user asks to:
- convert <amount> to
- currency for <country>
- exchange rate

## Core Workflows

GET `https://open.er-api.com/v6/latest/<BASE>` for live rate conversion.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
