---
name: blockchain-sign-message
description: Sign messages with an Ethereum private key for authentication.
---

# Message Signer Skill

## Purpose
Sign messages with an Ethereum private key for authentication.

## When to Activate
Activate when the user asks to:
- sign message
- wallet signature
- prove ownership
- sign with key

## Core Workflows

```python
from web3 import Web3; Web3().eth.account.sign_message(msg, private_key=pk)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
