---
name: legal-contract-review
description: Identify risky clauses and summarize key terms in contracts.
---

# Contract Reviewer Skill

## Purpose
Identify risky clauses and summarize key terms in contracts.

## When to Activate
Activate when the user asks to:
- review contract
- risky clauses
- contract analysis
- flag issues

## Core Workflows

Prompt: `Review this contract. Identify: risky clauses, missing standard protections, red flags, and a risk summary: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
