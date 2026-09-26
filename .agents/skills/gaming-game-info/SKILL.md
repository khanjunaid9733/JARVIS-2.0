---
name: gaming-game-info
description: Look up game details, ratings, and reviews from RAWG or IGDB.
---

# Game Info Lookup Skill

## Purpose
Look up game details, ratings, and reviews from RAWG or IGDB.

## When to Activate
Activate when the user asks to:
- game info
- tell me about game
- game rating
- game reviews

## Core Workflows

GET RAWG API `/api/games/{id}` for details, rating, genres, platforms.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
