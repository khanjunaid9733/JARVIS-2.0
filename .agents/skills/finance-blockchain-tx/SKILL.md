---
name: finance-blockchain-tx
description: Look up transaction details on Ethereum or Bitcoin blockchain.
---

# Blockchain Transaction Lookup Skill

## Purpose
Look up transaction details on Ethereum or Bitcoin blockchain.

## When to Activate
Activate when the user asks to:
- transaction status
- blockchain tx
- check transaction hash

## Core Workflows

GET Etherscan API `/api?module=transaction&action=gettxreceiptstatus&txhash=<hash>`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
