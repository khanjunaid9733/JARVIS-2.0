---
name: edu-math-solve
description: Solve and explain math problems step by step.
---

# Math Problem Solver Skill

## Purpose
Solve and explain math problems step by step.

## When to Activate
Activate when the user asks to:
- solve this math
- help with equation
- integrate
- differentiate
- algebra

## Core Workflows

Use SymPy for symbolic math: `sympy.solve()`, `sympy.diff()`, `sympy.integrate()`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
