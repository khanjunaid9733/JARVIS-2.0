---
name: ds-hyperparameter-tune
description: Find optimal model hyperparameters using GridSearch or Optuna.
---

# Hyperparameter Tuning Skill

## Purpose
Find optimal model hyperparameters using GridSearch or Optuna.

## When to Activate
Activate when the user asks to:
- tune hyperparameters
- GridSearchCV
- optimize model
- Optuna

## Core Workflows

```python
from sklearn.model_selection import GridSearchCV; GridSearchCV(model, params_grid, cv=5)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
