---
name: finance-dividend-tracker
description: Track dividend history and upcoming payment dates for stocks.
---

# Dividend Tracker Skill

## Purpose
Track dividend history and upcoming payment dates for stocks.

## When to Activate
Activate when the user asks to:
- dividend info
- when is dividend
- dividend yield

## Core Workflows

GET Yahoo Finance or Alpha Vantage dividend endpoint for ticker.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
