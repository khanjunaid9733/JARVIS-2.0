---
name: health-posture-remind
description: Remind to take posture breaks and stretch during desk work.
---

# Posture & Break Reminder Skill

## Purpose
Remind to take posture breaks and stretch during desk work.

## When to Activate
Activate when the user asks to:
- posture reminder
- desk break
- take a break
- stand up

## Core Workflows

Schedule timed notifications every 30-60 min with posture tips and stretch prompts.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
