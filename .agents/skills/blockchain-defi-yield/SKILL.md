---
name: blockchain-defi-yield
description: Compare yields across DeFi protocols (Aave, Compound, Curve).
---

# DeFi Yield Aggregator Skill

## Purpose
Compare yields across DeFi protocols (Aave, Compound, Curve).

## When to Activate
Activate when the user asks to:
- DeFi yield
- best APY
- staking returns
- yield farming

## Core Workflows

GET DeFi Llama `/yields/pools` API. Filter by chain + protocol + APY.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
