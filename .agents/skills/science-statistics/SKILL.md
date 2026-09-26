---
name: science-statistics
description: Compute mean, median, mode, variance, standard deviation, and distributions.
---

# Statistics Calculator Skill

## Purpose
Compute mean, median, mode, variance, standard deviation, and distributions.

## When to Activate
Activate when the user asks to:
- calculate mean
- standard deviation
- statistics
- probability

## Core Workflows

```python
import statistics; statistics.mean(data); statistics.stdev(data)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
