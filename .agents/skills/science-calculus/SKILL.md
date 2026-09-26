---
name: science-calculus
description: Differentiate and integrate symbolic expressions with SymPy.
---

# Calculus Solver Skill

## Purpose
Differentiate and integrate symbolic expressions with SymPy.

## When to Activate
Activate when the user asks to:
- differentiate
- integrate
- derivative of
- integral of
- limit

## Core Workflows

```python
import sympy as sp; f = sp.sin(x); sp.diff(f, x); sp.integrate(f, x)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
