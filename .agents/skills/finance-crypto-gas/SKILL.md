---
name: finance-crypto-gas
description: Check current ETH gas prices in Gwei.
---

# Ethereum Gas Tracker Skill

## Purpose
Check current ETH gas prices in Gwei.

## When to Activate
Activate when the user asks to:
- gas price
- Ethereum gas
- ETH gas fee

## Core Workflows

GET `https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey=<KEY>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
