---
name: gaming-leaderboard
description: Track and display game leaderboard positions.
---

# Game Leaderboard Tracker Skill

## Purpose
Track and display game leaderboard positions.

## When to Activate
Activate when the user asks to:
- leaderboard
- my rank
- top players
- ranking

## Core Workflows

Query game-specific API (Steam, PlayStation Network, Xbox Live) for leaderboard data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
