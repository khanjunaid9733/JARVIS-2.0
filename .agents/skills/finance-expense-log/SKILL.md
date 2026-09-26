---
name: finance-expense-log
description: Log and categorize personal expenses.
---

# Expense Logger Skill

## Purpose
Log and categorize personal expenses.

## When to Activate
Activate when the user asks to:
- log expense
- I spent
- bought <item>
- expense entry

## Core Workflows

Append to JARVIS_HOME/expenses.csv with date, amount, category, description.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
