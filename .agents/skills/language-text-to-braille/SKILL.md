---
name: language-text-to-braille
description: Convert text to Grade 1 Braille notation.
---

# Braille Converter Skill

## Purpose
Convert text to Grade 1 Braille notation.

## When to Activate
Activate when the user asks to:
- convert to braille
- braille text
- accessibility
- braille encode

## Core Workflows

Map ASCII characters to Unicode Braille patterns (U+2800–U+28FF).

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
