---
name: finance-portfolio
description: Track the value and performance of investment portfolios.
---

# Portfolio Tracker Skill

## Purpose
Track the value and performance of investment portfolios.

## When to Activate
Activate when the user asks to:
- portfolio value
- my investments
- portfolio performance

## Core Workflows

Sum asset quantities × current prices, compute gain/loss %.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
