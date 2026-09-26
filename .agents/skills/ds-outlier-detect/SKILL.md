---
name: ds-outlier-detect
description: Identify and handle outliers using IQR or Z-score methods.
---

# Outlier Detection Skill

## Purpose
Identify and handle outliers using IQR or Z-score methods.

## When to Activate
Activate when the user asks to:
- detect outliers
- find anomalies
- remove outliers

## Core Workflows

IQR: Q1 - 1.5×IQR to Q3 + 1.5×IQR. Z-score: |z| > 3 = outlier.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
