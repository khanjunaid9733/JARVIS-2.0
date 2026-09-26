---
name: health-mental-health
description: Provide PHQ-2 style mood check-ins and mental wellness resources.
---

# Mental Health Check-In Skill

## Purpose
Provide PHQ-2 style mood check-ins and mental wellness resources.

## When to Activate
Activate when the user asks to:
- mental health
- how am I feeling
- mood check
- well-being

## Core Workflows

Ask 2-question PHQ-2 screen. Provide resources for low scores. Recommend professional help as appropriate.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
