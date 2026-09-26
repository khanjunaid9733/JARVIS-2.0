---
name: blockchain-block-info
description: Get information about any block on the blockchain.
---

# Block Explorer Skill

## Purpose
Get information about any block on the blockchain.

## When to Activate
Activate when the user asks to:
- block info
- latest block
- block number
- block data

## Core Workflows

```python
web3.eth.get_block('latest')  # or specific block number
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
