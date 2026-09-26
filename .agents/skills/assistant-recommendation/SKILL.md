---
name: assistant-recommendation
description: Recommend books, movies, shows, or products based on preferences.
---

# Personalized Recommender Skill

## Purpose
Recommend books, movies, shows, or products based on preferences.

## When to Activate
Activate when the user asks to:
- recommend
- suggest
- what should I watch
- book recommendation

## Core Workflows

Route through LLM with user preference profile context.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
