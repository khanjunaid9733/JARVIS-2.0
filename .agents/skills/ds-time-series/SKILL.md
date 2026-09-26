---
name: ds-time-series
description: Decompose, forecast, and visualize time series data.
---

# Time Series Analysis Skill

## Purpose
Decompose, forecast, and visualize time series data.

## When to Activate
Activate when the user asks to:
- time series forecast
- predict future values
- trend analysis
- ARIMA

## Core Workflows

```python
from statsmodels.tsa.arima.model import ARIMA; ARIMA(y, order=(1,1,1)).fit()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
