---
name: si-habit-stack
description: Design habit stacks using the James Clear method.
---

# Habit Stacking Designer Skill

## Purpose
Design habit stacks using the James Clear method.

## When to Activate
Activate when the user asks to:
- habit stack
- attach habit to
- after I will
- habit design

## Core Workflows

Format: `After I {current habit}, I will {new habit}` chains. Design 3 stacks.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
