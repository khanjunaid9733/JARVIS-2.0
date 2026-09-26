---
name: media-lyrics-fetch
description: Fetch song lyrics for any track.
---

# Lyrics Fetcher Skill

## Purpose
Fetch song lyrics for any track.

## When to Activate
Activate when the user asks to:
- lyrics for
- show lyrics
- what are the lyrics to

## Core Workflows

Use Genius API or Lyrics.ovh: `GET https://api.lyrics.ovh/v1/<artist>/<title>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
