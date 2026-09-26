---
name: gaming-stats
description: Look up player statistics for FPS, battle royale, or MOBA games.
---

# Player Stats Lookup Skill

## Purpose
Look up player statistics for FPS, battle royale, or MOBA games.

## When to Activate
Activate when the user asks to:
- my stats
- player stats
- K/D ratio
- win rate

## Core Workflows

Use game-specific APIs (Tracker.gg, Fortnite-API.com, R6Siege API).

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
