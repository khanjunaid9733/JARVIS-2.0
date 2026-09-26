---
name: health-medication-remind
description: Set and manage medication reminder schedules.
---

# Medication Reminder Skill

## Purpose
Set and manage medication reminder schedules.

## When to Activate
Activate when the user asks to:
- medication reminder
- remind me to take
- pill reminder
- medicine alert

## Core Workflows

Use JARVIS scheduler: trigger notification at dose times with medication name.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
