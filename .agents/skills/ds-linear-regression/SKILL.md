---
name: ds-linear-regression
description: Fit a linear regression model and report coefficients and R².
---

# Linear Regression Skill

## Purpose
Fit a linear regression model and report coefficients and R².

## When to Activate
Activate when the user asks to:
- linear regression
- predict with regression
- fit a model

## Core Workflows

```python
from sklearn.linear_model import LinearRegression; model.fit(X, y); model.coef_
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
