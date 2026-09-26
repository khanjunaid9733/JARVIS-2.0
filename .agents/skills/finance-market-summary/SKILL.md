---
name: finance-market-summary
description: Get a summary of major market indices at open/close.
---

# Market Summary Skill

## Purpose
Get a summary of major market indices at open/close.

## When to Activate
Activate when the user asks to:
- market summary
- how's the market
- S&P 500 today
- market overview

## Core Workflows

Fetch SPY, QQQ, BTC, ETH, DXY prices and compute daily change %.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
