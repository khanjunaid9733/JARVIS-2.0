---
name: media-slideshow
description: Create an image slideshow presentation from a folder.
---

# Slideshow Creator Skill

## Purpose
Create an image slideshow presentation from a folder.

## When to Activate
Activate when the user asks to:
- create slideshow
- image presentation
- photo show

## Core Workflows

Use Pillow + ImageTk or ffmpeg image2 muxer to create MP4 slideshow.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
