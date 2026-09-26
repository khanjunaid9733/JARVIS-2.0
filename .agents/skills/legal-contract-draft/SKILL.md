---
name: legal-contract-draft
description: Draft standard contracts, NDAs, SLAs, and agreements.
---

# Contract Drafter Skill

## Purpose
Draft standard contracts, NDAs, SLAs, and agreements.

## When to Activate
Activate when the user asks to:
- draft contract
- NDA
- service agreement
- terms of service

## Core Workflows

Prompt: `Draft a {contract_type} between {party_a} and {party_b}. Include: definitions, obligations, liability, term, termination.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
