---
name: media-subtitle-extract
description: Extract or generate subtitles from video files.
---

# Subtitle Extractor Skill

## Purpose
Extract or generate subtitles from video files.

## When to Activate
Activate when the user asks to:
- extract subtitles
- get captions
- subtitle <video>

## Core Workflows

Use `ffmpeg -i video.mp4 subtitles.srt` or Whisper for AI-generated captions.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
