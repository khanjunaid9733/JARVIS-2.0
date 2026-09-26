---
name: pm-meeting-agenda
description: Create structured meeting agendas with time allocations.
---

# Meeting Agenda Builder Skill

## Purpose
Create structured meeting agendas with time allocations.

## When to Activate
Activate when the user asks to:
- meeting agenda
- create agenda
- schedule meeting topics

## Core Workflows

Prompt: `Create a {duration}-minute meeting agenda for {topic} with time-boxed sections and objectives.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
