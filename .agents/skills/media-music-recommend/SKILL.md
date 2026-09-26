---
name: media-music-recommend
description: Recommend music based on mood, genre, or artist preferences.
---

# Music Recommender Skill

## Purpose
Recommend music based on mood, genre, or artist preferences.

## When to Activate
Activate when the user asks to:
- recommend music
- songs like
- similar to
- playlist for

## Core Workflows

Use Spotify Recommendations API or Last.fm similar artists endpoint.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
