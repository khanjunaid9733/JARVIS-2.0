---
name: blockchain-tx-history
description: Fetch transaction history for any blockchain address.
---

# Transaction History Skill

## Purpose
Fetch transaction history for any blockchain address.

## When to Activate
Activate when the user asks to:
- transaction history
- wallet transactions
- past transfers

## Core Workflows

GET Etherscan API `?module=account&action=txlist&address=<addr>`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
