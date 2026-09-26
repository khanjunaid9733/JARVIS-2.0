---
name: ds-model-evaluate
description: Compute precision, recall, F1, AUC-ROC, and confusion matrix.
---

# Model Evaluation Skill

## Purpose
Compute precision, recall, F1, AUC-ROC, and confusion matrix.

## When to Activate
Activate when the user asks to:
- evaluate model
- model metrics
- F1 score
- precision recall
- AUC

## Core Workflows

```python
from sklearn.metrics import classification_report, roc_auc_score
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
