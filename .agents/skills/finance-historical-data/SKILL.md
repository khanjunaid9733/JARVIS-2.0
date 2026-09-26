---
name: finance-historical-data
description: Fetch OHLCV historical price data for any asset.
---

# Historical Price Data Skill

## Purpose
Fetch OHLCV historical price data for any asset.

## When to Activate
Activate when the user asks to:
- historical price
- chart data
- price history for

## Core Workflows

GET `https://query1.finance.yahoo.com/v8/finance/chart/<ticker>?range=1y&interval=1d`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
