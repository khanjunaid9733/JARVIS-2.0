---
name: comm-language-detect
description: Detect the language of any incoming text message.
---

# Message Language Detector Skill

## Purpose
Detect the language of any incoming text message.

## When to Activate
Activate when the user asks to:
- what language is this
- detect language
- identify language

## Core Workflows

Use `langdetect` library: `detect(text)` returns ISO 639-1 code.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
