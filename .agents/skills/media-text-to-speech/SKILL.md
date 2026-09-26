---
name: media-text-to-speech
description: Convert any text to spoken audio using TTS engines.
---

# Text to Speech Skill

## Purpose
Convert any text to spoken audio using TTS engines.

## When to Activate
Activate when the user asks to:
- say this aloud
- speak
- text to speech
- read this out

## Core Workflows

Use Piper TTS, Windows SAPI, or ElevenLabs API to generate WAV.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
