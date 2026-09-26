---
name: finance-compound-interest
description: Calculate compound interest and future value of investments.
---

# Compound Interest Calculator Skill

## Purpose
Calculate compound interest and future value of investments.

## When to Activate
Activate when the user asks to:
- compound interest
- future value
- investment calculator

## Core Workflows

FV = P × (1 + r/n)^(nt). Return principal, interest earned, final value.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
