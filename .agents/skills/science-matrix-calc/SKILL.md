---
name: science-matrix-calc
description: Perform matrix operations: multiplication, inversion, determinant, eigenvalues.
---

# Matrix Calculator Skill

## Purpose
Perform matrix operations: multiplication, inversion, determinant, eigenvalues.

## When to Activate
Activate when the user asks to:
- matrix multiply
- invert matrix
- eigenvalues
- determinant

## Core Workflows

```python
import numpy as np; np.linalg.inv(A); np.linalg.eig(A)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
