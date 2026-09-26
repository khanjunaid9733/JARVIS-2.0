---
name: photo-slideshow-mp4
description: Convert a folder of images into an MP4 slideshow video.
---

# Slideshow to MP4 Skill

## Purpose
Convert a folder of images into an MP4 slideshow video.

## When to Activate
Activate when the user asks to:
- slideshow video
- images to video
- photo video
- create MP4 from photos

## Core Workflows

```bash
ffmpeg -framerate 1 -pattern_type glob -i '*.jpg' -c:v libx264 -pix_fmt yuv420p output.mp4
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
