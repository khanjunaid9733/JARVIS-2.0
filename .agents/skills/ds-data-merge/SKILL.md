---
name: ds-data-merge
description: Merge, join, and concatenate multiple datasets.
---

# Dataset Merger Skill

## Purpose
Merge, join, and concatenate multiple datasets.

## When to Activate
Activate when the user asks to:
- merge datasets
- join tables
- combine CSV files
- left join

## Core Workflows

```python
pd.merge(df1, df2, on='key', how='left')  # or pd.concat([df1, df2])
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
