---
name: media-screen-record
description: Record the screen as a video file.
---

# Screen Recorder Skill

## Purpose
Record the screen as a video file.

## When to Activate
Activate when the user asks to:
- record screen
- capture screen video
- start recording

## Core Workflows

Use ffmpeg with desktop capture: `ffmpeg -f gdigrab -i desktop output.mp4`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
