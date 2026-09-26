---
name: ds-classification
description: Train a classification model (Random Forest, SVM, etc.) and evaluate.
---

# Classification Model Skill

## Purpose
Train a classification model (Random Forest, SVM, etc.) and evaluate.

## When to Activate
Activate when the user asks to:
- train classifier
- classification model
- predict class
- train ML model

## Core Workflows

```python
from sklearn.ensemble import RandomForestClassifier; clf.fit(X_train, y_train)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
