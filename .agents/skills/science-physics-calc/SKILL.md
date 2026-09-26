---
name: science-physics-calc
description: Solve physics problems using formulas from classical mechanics.
---

# Physics Calculator Skill

## Purpose
Solve physics problems using formulas from classical mechanics.

## When to Activate
Activate when the user asks to:
- physics formula
- kinetic energy
- force calculation
- velocity
- acceleration

## Core Workflows

```python
import sympy; # define variables, apply formula, solve symbolically
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
