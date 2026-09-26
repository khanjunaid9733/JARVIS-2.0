---
name: media-speech-to-text
description: Transcribe audio files or microphone input to text.
---

# Speech to Text Skill

## Purpose
Transcribe audio files or microphone input to text.

## When to Activate
Activate when the user asks to:
- transcribe
- speech to text
- convert audio to text

## Core Workflows

Use Whisper CLI or API: `whisper audio.wav --model base --language en`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
