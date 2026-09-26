---
name: gaming-event-calendar
description: Track upcoming in-game events, season passes, and content drops.
---

# Game Events Calendar Skill

## Purpose
Track upcoming in-game events, season passes, and content drops.

## When to Activate
Activate when the user asks to:
- game events
- when is season
- in-game event
- content release

## Core Workflows

Fetch from game publisher API or community wikis, display upcoming dates.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
