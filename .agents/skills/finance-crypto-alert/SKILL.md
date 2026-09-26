---
name: finance-crypto-alert
description: Alert when a crypto price crosses a threshold.
---

# Crypto Price Alert Skill

## Purpose
Alert when a crypto price crosses a threshold.

## When to Activate
Activate when the user asks to:
- alert when bitcoin hits
- notify when <coin> is above
- price alert

## Core Workflows

Poll CoinGecko API every 5 min, compare to threshold, trigger notification.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
