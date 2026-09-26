---
name: finance-price
description: Get real-time prices for stocks, ETFs, forex, and crypto.
---

# Asset Price Tracker Skill

## Purpose
Get real-time prices for stocks, ETFs, forex, and crypto.

## When to Activate
Activate when the user asks to:
- price of
- stock price
- bitcoin price
- what's <ticker> at

## Core Workflows

GET Yahoo Finance or CoinGecko API for current market price.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
