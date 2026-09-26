---
name: blockchain-token-price
description: Get real-time price of any DeFi token via CoinGecko.
---

# Token Price Tracker Skill

## Purpose
Get real-time price of any DeFi token via CoinGecko.

## When to Activate
Activate when the user asks to:
- token price
- coin price
- crypto price
- price of <token>

## Core Workflows

GET `https://api.coingecko.com/api/v3/simple/price?ids=<id>&vs_currencies=usd`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
