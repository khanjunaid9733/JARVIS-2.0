---
name: media-video-convert
description: Convert video files between MP4, MKV, AVI, WebM formats.
---

# Video Converter Skill

## Purpose
Convert video files between MP4, MKV, AVI, WebM formats.

## When to Activate
Activate when the user asks to:
- convert video
- convert to MP4
- video format change

## Core Workflows

```bash
ffmpeg -i input.mkv -c:v libx264 output.mp4
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
