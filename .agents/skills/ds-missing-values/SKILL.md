---
name: ds-missing-values
description: Detect, impute, or drop missing values in datasets.
---

# Missing Value Handler Skill

## Purpose
Detect, impute, or drop missing values in datasets.

## When to Activate
Activate when the user asks to:
- missing values
- fill NaN
- drop nulls
- handle missing data

## Core Workflows

```python
df.isnull().sum(); df.fillna(df.mean())  # or df.dropna()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
