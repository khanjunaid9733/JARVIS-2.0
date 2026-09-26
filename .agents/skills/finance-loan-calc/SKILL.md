---
name: finance-loan-calc
description: Calculate monthly payments, total interest, and amortization schedule.
---

# Loan Calculator Skill

## Purpose
Calculate monthly payments, total interest, and amortization schedule.

## When to Activate
Activate when the user asks to:
- loan payment
- mortgage calculator
- monthly payment for loan

## Core Workflows

M = P × r(1+r)^n / ((1+r)^n - 1). Return payment, total interest, amortization table.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
