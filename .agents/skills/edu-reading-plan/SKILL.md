---
name: edu-reading-plan
description: Create a structured reading plan for books or courses.
---

# Reading Plan Creator Skill

## Purpose
Create a structured reading plan for books or courses.

## When to Activate
Activate when the user asks to:
- reading plan
- study schedule
- reading list
- learn <topic> in <time>

## Core Workflows

Break material into chunks, schedule by days/weeks, set milestones.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
