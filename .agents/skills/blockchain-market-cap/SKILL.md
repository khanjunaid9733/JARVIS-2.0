---
name: blockchain-market-cap
description: Track market cap rankings for top cryptocurrencies.
---

# Crypto Market Cap Tracker Skill

## Purpose
Track market cap rankings for top cryptocurrencies.

## When to Activate
Activate when the user asks to:
- market cap
- crypto rankings
- top coins by market cap

## Core Workflows

GET CoinGecko `/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
