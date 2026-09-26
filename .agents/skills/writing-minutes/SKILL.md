---
name: writing-minutes
description: Convert meeting notes into formatted official minutes.
---

# Meeting Minutes Writer Skill

## Purpose
Convert meeting notes into formatted official minutes.

## When to Activate
Activate when the user asks to:
- meeting minutes
- format meeting notes
- official minutes

## Core Workflows

Prompt: `Convert these meeting notes into formal meeting minutes with attendees, agenda, decisions, action items: {notes}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
