---
name: blockchain-audit-contract
description: Perform basic security audit of Solidity smart contract code.
---

# Smart Contract Auditor Skill

## Purpose
Perform basic security audit of Solidity smart contract code.

## When to Activate
Activate when the user asks to:
- audit contract
- smart contract security
- Solidity audit
- reentrancy check

## Core Workflows

Check for: reentrancy, integer overflow, access control, unchecked calls using Slither or LLM analysis.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
