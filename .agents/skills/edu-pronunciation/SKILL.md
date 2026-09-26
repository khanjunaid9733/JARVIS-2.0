---
name: edu-pronunciation
description: Provide phonetic pronunciation guides for words or phrases.
---

# Pronunciation Guide Skill

## Purpose
Provide phonetic pronunciation guides for words or phrases.

## When to Activate
Activate when the user asks to:
- how to pronounce
- pronunciation of
- phonetics

## Core Workflows

Prompt: `Provide IPA phonetic transcription and pronunciation tips for: {words}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
