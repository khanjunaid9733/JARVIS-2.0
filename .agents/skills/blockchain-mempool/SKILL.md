---
name: blockchain-mempool
description: Monitor the Ethereum mempool for pending transactions.
---

# Mempool Monitor Skill

## Purpose
Monitor the Ethereum mempool for pending transactions.

## When to Activate
Activate when the user asks to:
- mempool
- pending transactions
- unconfirmed tx
- mempool monitor

## Core Workflows

Use web3 filter: `web3.eth.filter('pending').get_new_entries()`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
