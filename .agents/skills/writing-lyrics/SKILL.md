---
name: writing-lyrics
description: Write original song lyrics with chorus, verses, and bridge.
---

# Song Lyrics Writer Skill

## Purpose
Write original song lyrics with chorus, verses, and bridge.

## When to Activate
Activate when the user asks to:
- write lyrics
- song about
- music lyrics

## Core Workflows

Prompt: `Write lyrics for a {genre} song about {theme}. Include intro, verse 1, chorus, verse 2, bridge.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
