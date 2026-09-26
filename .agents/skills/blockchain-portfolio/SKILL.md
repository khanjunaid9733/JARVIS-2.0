---
name: blockchain-portfolio
description: Track a multi-asset crypto portfolio's total value.
---

# Crypto Portfolio Tracker Skill

## Purpose
Track a multi-asset crypto portfolio's total value.

## When to Activate
Activate when the user asks to:
- crypto portfolio
- token holdings
- portfolio value
- crypto wealth

## Core Workflows

Fetch balance × price for each asset, sum to total USD value.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
