---
name: assistant-decision-help
description: Help make decisions using pros/cons analysis and decision frameworks.
---

# Decision Helper Skill

## Purpose
Help make decisions using pros/cons analysis and decision frameworks.

## When to Activate
Activate when the user asks to:
- help me decide
- pros and cons
- should I
- decision support

## Core Workflows

Prompt: `Analyze this decision: {options}. Create a weighted pros/cons matrix and recommend.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
