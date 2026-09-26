---
name: science-chemistry
description: Look up chemical compounds, reactions, and properties.
---

# Chemistry Assistant Skill

## Purpose
Look up chemical compounds, reactions, and properties.

## When to Activate
Activate when the user asks to:
- chemical formula
- compound info
- reaction of
- molar mass of

## Core Workflows

Use PubChem API or Wolfram Alpha API for chemical data and properties.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
