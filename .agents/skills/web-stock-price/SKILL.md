---
name: web-stock-price
description: Get real-time stock or crypto prices via Yahoo Finance API.
---

# Stock Price Lookup Skill

## Purpose
Get real-time stock or crypto prices via Yahoo Finance API.

## When to Activate
Activate when the user asks to:
- stock price of <ticker>
- what is the price of AAPL
- bitcoin price

## Core Workflows

GET `https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?interval=1d&range=1d`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
