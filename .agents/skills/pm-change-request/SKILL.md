---
name: pm-change-request
description: Process, evaluate, and document project change requests.
---

# Change Request Manager Skill

## Purpose
Process, evaluate, and document project change requests.

## When to Activate
Activate when the user asks to:
- change request
- scope change
- feature addition request
- change control

## Core Workflows

Prompt: `Evaluate this change request for {project}: {change}. Assess impact on: scope, time, cost, risk.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
