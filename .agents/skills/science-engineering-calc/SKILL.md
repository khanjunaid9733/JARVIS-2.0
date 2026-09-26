---
name: science-engineering-calc
description: Solve structural, electrical, or fluid engineering problems.
---

# Engineering Calculator Skill

## Purpose
Solve structural, electrical, or fluid engineering problems.

## When to Activate
Activate when the user asks to:
- engineering formula
- beam deflection
- resistor circuit
- fluid flow

## Core Workflows

Apply domain-specific formulas (Euler beam, Ohm's law, Bernoulli) via SymPy.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
