---
name: media-audio-convert
description: Convert audio files between MP3, WAV, FLAC, AAC formats.
---

# Audio Converter Skill

## Purpose
Convert audio files between MP3, WAV, FLAC, AAC formats.

## When to Activate
Activate when the user asks to:
- convert audio
- convert to MP3
- audio format change

## Core Workflows

```bash
ffmpeg -i input.wav -q:a 0 output.mp3
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
