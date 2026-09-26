---
name: gaming-achievement-track
description: Track and display Steam or console achievements.
---

# Achievement Tracker Skill

## Purpose
Track and display Steam or console achievements.

## When to Activate
Activate when the user asks to:
- achievements
- trophy count
- 100% achievements
- what achievements do I have

## Core Workflows

GET Steam API `ISteamUserStats/GetPlayerAchievements/v0001/?appid=<id>&steamid=<id>`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
