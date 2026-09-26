---
name: gaming-game-library
description: List, search, and manage your Steam game library.
---

# Game Library Manager Skill

## Purpose
List, search, and manage your Steam game library.

## When to Activate
Activate when the user asks to:
- my games
- Steam library
- what games do I own
- installed games

## Core Workflows

GET Steam API `IPlayerService/GetOwnedGames/v0001/?steamid=<id>`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
