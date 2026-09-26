---
name: blockchain-layer2
description: Get bridging fees and estimated times for L2 solutions.
---

# Layer 2 Bridge Info Skill

## Purpose
Get bridging fees and estimated times for L2 solutions.

## When to Activate
Activate when the user asks to:
- Layer 2
- bridge to Polygon
- Arbitrum fees
- bridge ETH

## Core Workflows

GET Biconomy or official bridge APIs for current fees and confirmation times.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
