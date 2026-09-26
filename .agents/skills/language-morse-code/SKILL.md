---
name: language-morse-code
description: Encode and decode Morse code.
---

# Morse Code Converter Skill

## Purpose
Encode and decode Morse code.

## When to Activate
Activate when the user asks to:
- morse code
- encode morse
- decode morse
- dots and dashes

## Core Workflows

Map characters to Morse patterns. Decode by splitting on word/letter separators.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
