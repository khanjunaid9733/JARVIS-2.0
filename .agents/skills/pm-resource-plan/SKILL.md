---
name: pm-resource-plan
description: Plan team resource allocation across projects.
---

# Resource Plan Skill

## Purpose
Plan team resource allocation across projects.

## When to Activate
Activate when the user asks to:
- resource allocation
- team capacity
- who works on
- assign people

## Core Workflows

Calculate availability hours per person, allocate to tasks, flag over-allocation.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
