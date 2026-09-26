---
name: media-youtube-search
description: Search YouTube for videos and return top results with links.
---

# YouTube Video Search Skill

## Purpose
Search YouTube for videos and return top results with links.

## When to Activate
Activate when the user asks to:
- search YouTube for
- find YouTube video
- YouTube <topic>

## Core Workflows

GET `https://www.googleapis.com/youtube/v3/search?part=snippet&q=<query>&key=<KEY>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
