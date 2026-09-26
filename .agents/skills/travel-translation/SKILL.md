---
name: travel-translation
description: Translate common travel phrases into the local language.
---

# Travel Phrase Translator Skill

## Purpose
Translate common travel phrases into the local language.

## When to Activate
Activate when the user asks to:
- how do you say in <language>
- translate phrase
- travel translation

## Core Workflows

Use LibreTranslate API with a catalog of 50 common travel phrases.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
