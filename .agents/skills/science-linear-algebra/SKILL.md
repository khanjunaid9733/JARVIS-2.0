---
name: science-linear-algebra
description: Solve systems of linear equations and matrix decompositions.
---

# Linear Algebra Solver Skill

## Purpose
Solve systems of linear equations and matrix decompositions.

## When to Activate
Activate when the user asks to:
- solve linear equations
- Ax=b
- LU decomposition
- SVD

## Core Workflows

```python
np.linalg.solve(A, b)  # or sp.solve([eq1, eq2], [x, y])
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
