---
name: blockchain-gas-price
description: Get current Ethereum gas prices in Gwei across speed tiers.
---

# Gas Price Oracle Skill

## Purpose
Get current Ethereum gas prices in Gwei across speed tiers.

## When to Activate
Activate when the user asks to:
- gas price
- ETH gas
- transaction fee
- slow/fast gas

## Core Workflows

GET `https://api.etherscan.io/api?module=gastracker&action=gasoracle`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
