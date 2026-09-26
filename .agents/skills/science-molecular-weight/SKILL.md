---
name: science-molecular-weight
description: Calculate the molecular weight of any chemical formula.
---

# Molecular Weight Calculator Skill

## Purpose
Calculate the molecular weight of any chemical formula.

## When to Activate
Activate when the user asks to:
- molecular weight
- molar mass
- atomic weight
- formula mass

## Core Workflows

Parse chemical formula, sum atomic masses from periodic table lookup.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
