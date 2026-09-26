---
name: gaming-recommend
description: Recommend games based on genre, platform, and preferences.
---

# Game Recommender Skill

## Purpose
Recommend games based on genre, platform, and preferences.

## When to Activate
Activate when the user asks to:
- recommend games
- games like
- what game to play
- game suggestions

## Core Workflows

Filter RAWG API by genre + platform + rating > 80. Return top 5 recommendations.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
