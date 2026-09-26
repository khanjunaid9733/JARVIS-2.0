---
name: assistant-event-planner
description: Plan parties, events, and gatherings with checklists and timelines.
---

# Event Planner Skill

## Purpose
Plan parties, events, and gatherings with checklists and timelines.

## When to Activate
Activate when the user asks to:
- plan event
- party planning
- event checklist
- organize gathering

## Core Workflows

Prompt: `Create a comprehensive event plan for a {event_type} with {guests} guests. Include timeline, checklist, vendors.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
