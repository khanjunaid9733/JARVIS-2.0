---
name: science-equation-solver
description: Solve algebraic, differential, and transcendental equations.
---

# Equation Solver Skill

## Purpose
Solve algebraic, differential, and transcendental equations.

## When to Activate
Activate when the user asks to:
- solve equation
- find x
- solve for
- equation solving

## Core Workflows

```python
sp.solve(sp.Eq(x**2 - 5, 0), x)  # or sp.dsolve for ODEs
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
