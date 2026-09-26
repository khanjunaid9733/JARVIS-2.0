---
name: photo-video-thumbnail
description: Extract thumbnail frames from video files.
---

# Video Thumbnail Extractor Skill

## Purpose
Extract thumbnail frames from video files.

## When to Activate
Activate when the user asks to:
- video thumbnail
- frame from video
- video screenshot

## Core Workflows

```bash
ffmpeg -i video.mp4 -ss 00:00:10 -vframes 1 thumbnail.jpg
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
