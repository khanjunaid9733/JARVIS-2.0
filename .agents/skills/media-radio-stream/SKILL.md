---
name: media-radio-stream
description: Stream internet radio stations by genre or name.
---

# Internet Radio Player Skill

## Purpose
Stream internet radio stations by genre or name.

## When to Activate
Activate when the user asks to:
- play radio
- tune into <station>
- internet radio

## Core Workflows

Use Radio Browser API to find stream URL, play via VLC subprocess.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
