---
name: assistant-birthday-remind
description: Track and remind about upcoming birthdays.
---

# Birthday Reminder Skill

## Purpose
Track and remind about upcoming birthdays.

## When to Activate
Activate when the user asks to:
- birthday reminder
- upcoming birthdays
- when is <name> birthday

## Core Workflows

Store birthdays in JARVIS_HOME/birthdays.yaml, alert 7 days and day-of.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
