---
name: gaming-game-review
description: Write detailed game reviews from experience or notes.
---

# AI Game Review Writer Skill

## Purpose
Write detailed game reviews from experience or notes.

## When to Activate
Activate when the user asks to:
- game review
- review <game>
- write review for game

## Core Workflows

Prompt: `Write a 500-word review of {game}. Cover: graphics, gameplay, story, value, and final verdict/score.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
