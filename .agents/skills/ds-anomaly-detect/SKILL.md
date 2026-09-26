---
name: ds-anomaly-detect
description: Detect anomalies in time series or tabular data using Isolation Forest.
---

# Anomaly Detection Skill

## Purpose
Detect anomalies in time series or tabular data using Isolation Forest.

## When to Activate
Activate when the user asks to:
- anomaly detection
- find anomalies
- detect outliers in time series

## Core Workflows

```python
from sklearn.ensemble import IsolationForest; IsolationForest().fit_predict(X)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
