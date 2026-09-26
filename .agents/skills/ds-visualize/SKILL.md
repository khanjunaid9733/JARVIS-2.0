---
name: ds-visualize
description: Generate charts: bar, line, scatter, histogram, pie, heatmap.
---

# Data Visualizer Skill

## Purpose
Generate charts: bar, line, scatter, histogram, pie, heatmap.

## When to Activate
Activate when the user asks to:
- plot data
- create chart
- visualize
- bar chart
- scatter plot

## Core Workflows

```python
import matplotlib.pyplot as plt; df.plot(kind='bar'); plt.savefig('chart.png')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
