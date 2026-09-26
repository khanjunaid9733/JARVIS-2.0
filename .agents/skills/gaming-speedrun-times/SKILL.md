---
name: gaming-speedrun-times
description: Look up world record speedrun times for any game.
---

# Speedrun Time Lookup Skill

## Purpose
Look up world record speedrun times for any game.

## When to Activate
Activate when the user asks to:
- speedrun
- world record
- fastest time
- any%

## Core Workflows

GET Speedrun.com API `/api/v1/games?name=<game>` then `/runs?game=<id>&orderby=times.primary_t`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
