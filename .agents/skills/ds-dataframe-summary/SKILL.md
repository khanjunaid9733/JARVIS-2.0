---
name: ds-dataframe-summary
description: Load a CSV/JSON dataset and compute descriptive statistics.
---

# DataFrame Summary Skill

## Purpose
Load a CSV/JSON dataset and compute descriptive statistics.

## When to Activate
Activate when the user asks to:
- summarize dataset
- data stats
- describe data
- dataset summary

## Core Workflows

```python
import pandas as pd; df = pd.read_csv(path); print(df.describe(), df.dtypes)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
