---
name: ds-correlation
description: Compute and visualize correlation matrices between numeric features.
---

# Correlation Analysis Skill

## Purpose
Compute and visualize correlation matrices between numeric features.

## When to Activate
Activate when the user asks to:
- correlation matrix
- feature correlations
- which features are related

## Core Workflows

```python
df.corr().style.background_gradient()  # or seaborn heatmap
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
