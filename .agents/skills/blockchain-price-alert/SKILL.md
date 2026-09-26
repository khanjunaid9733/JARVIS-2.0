---
name: blockchain-price-alert
description: Alert when a crypto token reaches a price threshold.
---

# Crypto Price Alert Bot Skill

## Purpose
Alert when a crypto token reaches a price threshold.

## When to Activate
Activate when the user asks to:
- alert when bitcoin
- price alert crypto
- notify when ETH hits

## Core Workflows

Poll CoinGecko every 5 minutes, compare to threshold, send Telegram/Discord alert.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
