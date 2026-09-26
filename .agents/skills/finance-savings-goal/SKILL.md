---
name: finance-savings-goal
description: Track progress toward a savings target with milestones.
---

# Savings Goal Tracker Skill

## Purpose
Track progress toward a savings target with milestones.

## When to Activate
Activate when the user asks to:
- savings goal
- save for
- how long to save for
- savings tracker

## Core Workflows

Calculate months to goal = (goal - saved) / monthly_savings. Show timeline.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
