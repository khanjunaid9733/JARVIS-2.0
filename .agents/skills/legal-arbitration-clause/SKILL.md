---
name: legal-arbitration-clause
description: Draft arbitration and dispute resolution clauses.
---

# Arbitration Clause Writer Skill

## Purpose
Draft arbitration and dispute resolution clauses.

## When to Activate
Activate when the user asks to:
- arbitration clause
- dispute resolution
- mediation clause
- ADR

## Core Workflows

Prompt: `Draft an arbitration clause for a {contract_type} specifying: venue, rules (AAA/JAMS), governing law.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
