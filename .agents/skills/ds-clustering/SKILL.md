---
name: ds-clustering
description: Cluster data points using K-Means or DBSCAN.
---

# Data Clustering Skill

## Purpose
Cluster data points using K-Means or DBSCAN.

## When to Activate
Activate when the user asks to:
- cluster data
- K-means
- find groups in data
- unsupervised clustering

## Core Workflows

```python
from sklearn.cluster import KMeans; KMeans(n_clusters=5).fit(X).labels_
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
