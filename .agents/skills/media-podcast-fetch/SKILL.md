---
name: media-podcast-fetch
description: Find and download the latest episodes of any podcast.
---

# Podcast Episode Fetcher Skill

## Purpose
Find and download the latest episodes of any podcast.

## When to Activate
Activate when the user asks to:
- latest <podcast> episode
- download podcast
- find podcast

## Core Workflows

Fetch RSS feed, parse episodes, download MP3 via urllib.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
