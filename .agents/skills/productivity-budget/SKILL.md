---
name: productivity-budget
description: Track income, expenses, and savings goals.
---

# Personal Budget Tracker Skill

## Purpose
Track income, expenses, and savings goals.

## When to Activate
Activate when the user asks to:
- log expense
- track spending
- budget report
- how much did I spend

## Core Workflows

Store transactions in JARVIS_HOME/budget.csv, compute category totals.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
