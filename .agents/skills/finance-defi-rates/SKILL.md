---
name: finance-defi-rates
description: Fetch current DeFi lending and yield farming rates.
---

# DeFi Yield Rates Skill

## Purpose
Fetch current DeFi lending and yield farming rates.

## When to Activate
Activate when the user asks to:
- DeFi rates
- yield farming APY
- lending rates

## Core Workflows

GET DeFi Llama API: `https://yields.llama.fi/pools` for pool APY data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
