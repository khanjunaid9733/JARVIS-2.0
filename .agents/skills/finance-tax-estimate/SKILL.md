---
name: finance-tax-estimate
description: Estimate income tax liability based on income and jurisdiction.
---

# Tax Estimator Skill

## Purpose
Estimate income tax liability based on income and jurisdiction.

## When to Activate
Activate when the user asks to:
- estimate tax
- how much tax
- tax calculator

## Core Workflows

Apply progressive bracket rates for given jurisdiction to taxable income.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
