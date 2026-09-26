---
name: pm-burndown
description: Generate a burndown chart from story points and completion data.
---

# Burndown Chart Generator Skill

## Purpose
Generate a burndown chart from story points and completion data.

## When to Activate
Activate when the user asks to:
- burndown chart
- sprint progress
- remaining work
- velocity chart

## Core Workflows

Plot ideal burndown line vs actual completion. Use matplotlib to save PNG.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
