---
name: blockchain-decode-tx
description: Decode and explain an Ethereum transaction's input data.
---

# Transaction Decoder Skill

## Purpose
Decode and explain an Ethereum transaction's input data.

## When to Activate
Activate when the user asks to:
- decode transaction
- what did this tx do
- transaction data

## Core Workflows

Use ABI decoder with contract ABI to parse function call and parameters.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
