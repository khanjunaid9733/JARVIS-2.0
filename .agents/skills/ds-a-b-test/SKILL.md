---
name: ds-a-b-test
description: Perform statistical significance tests on A/B experiment results.
---

# A/B Test Analyzer Skill

## Purpose
Perform statistical significance tests on A/B experiment results.

## When to Activate
Activate when the user asks to:
- A/B test
- statistical significance
- compare variants
- chi-square test

## Core Workflows

Use `scipy.stats.chi2_contingency` for proportions, `ttest_ind` for means.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
