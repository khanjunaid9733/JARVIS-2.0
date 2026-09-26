---
name: finance-budget-calc
description: Calculate budget allocation by category (50/30/20 rule).
---

# Budget Calculator Skill

## Purpose
Calculate budget allocation by category (50/30/20 rule).

## When to Activate
Activate when the user asks to:
- budget calculator
- 50 30 20 rule
- how to budget income

## Core Workflows

Apply configurable percentage splits to income, return category allocations.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
