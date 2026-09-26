---
name: gaming-stream-info
description: Find currently live Twitch streams for any game or category.
---

# Twitch Stream Finder Skill

## Purpose
Find currently live Twitch streams for any game or category.

## When to Activate
Activate when the user asks to:
- live streams
- Twitch streams
- who is streaming
- watch <game>

## Core Workflows

GET Twitch API `/helix/streams?game_id=<id>` for live streams list.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
