---
name: comm-reminder
description: Set a reminder that fires a notification at a specific time.
---

# Reminder Scheduler Skill

## Purpose
Set a reminder that fires a notification at a specific time.

## When to Activate
Activate when the user asks to:
- remind me to
- set reminder
- alert me at

## Core Workflows

Use JARVIS AutonomousScheduler to queue a timed notification task.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
