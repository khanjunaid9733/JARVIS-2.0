---
name: language-pronunciation
description: Give IPA phonetic transcriptions and pronunciation tips.
---

# Pronunciation Guide Skill

## Purpose
Give IPA phonetic transcriptions and pronunciation tips.

## When to Activate
Activate when the user asks to:
- pronounce
- how to say
- IPA
- phonetics
- pronunciation of

## Core Workflows

Prompt: `Give IPA transcription and pronunciation guide for: {words} in {language}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
