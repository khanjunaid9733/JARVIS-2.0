---
name: blockchain-ens-lookup
description: Resolve Ethereum Name Service (ENS) domains to wallet addresses.
---

# ENS Name Resolver Skill

## Purpose
Resolve Ethereum Name Service (ENS) domains to wallet addresses.

## When to Activate
Activate when the user asks to:
- ENS name
- resolve .eth
- wallet address for name

## Core Workflows

```python
web3.ens.address('vitalik.eth')  # returns wallet address
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
