---
name: ds-dimensionality
description: Reduce feature dimensions using PCA or t-SNE for visualization.
---

# Dimensionality Reduction Skill

## Purpose
Reduce feature dimensions using PCA or t-SNE for visualization.

## When to Activate
Activate when the user asks to:
- PCA
- reduce dimensions
- t-SNE
- visualize high dimensional data

## Core Workflows

```python
from sklearn.decomposition import PCA; PCA(n_components=2).fit_transform(X)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
