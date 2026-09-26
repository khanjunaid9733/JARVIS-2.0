---
name: media-video-download
description: Download videos from YouTube, Twitter, Instagram using yt-dlp.
---

# Video Downloader Skill

## Purpose
Download videos from YouTube, Twitter, Instagram using yt-dlp.

## When to Activate
Activate when the user asks to:
- download video
- save YouTube video
- download from <url>

## Core Workflows

```bash
yt-dlp '<url>' -o 'downloads/%(title)s.%(ext)s'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
