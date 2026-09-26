---
name: ds-pipeline
description: Build an end-to-end scikit-learn ML pipeline with preprocessing.
---

# ML Pipeline Builder Skill

## Purpose
Build an end-to-end scikit-learn ML pipeline with preprocessing.

## When to Activate
Activate when the user asks to:
- build ML pipeline
- scikit-learn pipeline
- preprocessing pipeline

## Core Workflows

```python
from sklearn.pipeline import Pipeline; Pipeline([('scaler', StandardScaler()), ('clf', RandomForestClassifier())])
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
