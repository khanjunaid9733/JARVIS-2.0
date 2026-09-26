---
name: assistant-morning-brief
description: Deliver a personalized morning briefing with weather, calendar, news, tasks.
---

# Morning Briefing Skill

## Purpose
Deliver a personalized morning briefing with weather, calendar, news, tasks.

## When to Activate
Activate when the user asks to:
- morning briefing
- good morning
- start my day
- daily brief

## Core Workflows

Aggregate: weather → calendar events → top news → task list → motivational quote.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
