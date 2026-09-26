---
name: blockchain-dao-vote
description: Check active DAO proposals and voting status.
---

# DAO Governance Checker Skill

## Purpose
Check active DAO proposals and voting status.

## When to Activate
Activate when the user asks to:
- DAO vote
- governance proposal
- Snapshot
- on-chain vote

## Core Workflows

GET Snapshot API GraphQL `/graphql` for proposals by space.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
