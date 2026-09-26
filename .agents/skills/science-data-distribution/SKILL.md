---
name: science-data-distribution
description: Plot probability distributions: normal, Poisson, binomial, etc.
---

# Probability Distribution Plotter Skill

## Purpose
Plot probability distributions: normal, Poisson, binomial, etc.

## When to Activate
Activate when the user asks to:
- plot distribution
- probability distribution
- normal distribution
- bell curve

## Core Workflows

```python
from scipy import stats; stats.norm.pdf(x); plt.plot(x, y)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
