---
name: blockchain-smart-contract
description: Read data from Ethereum smart contracts via ABI calls.
---

# Smart Contract Caller Skill

## Purpose
Read data from Ethereum smart contracts via ABI calls.

## When to Activate
Activate when the user asks to:
- smart contract
- read contract
- call contract function
- ERC-20 contract

## Core Workflows

```python
from web3 import Web3; contract.functions.balanceOf(addr).call()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
