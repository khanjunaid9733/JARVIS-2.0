---
name: edu-history-timeline
description: Create visual historical timelines for any topic or period.
---

# History Timeline Creator Skill

## Purpose
Create visual historical timelines for any topic or period.

## When to Activate
Activate when the user asks to:
- history timeline
- historical events
- timeline of
- when did

## Core Workflows

Prompt: `Create a detailed timeline of {topic} from {start} to {end}. Format as a chronological list.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
