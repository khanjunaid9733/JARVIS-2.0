---
name: edu-translate-text
description: Translate text between 100+ languages.
---

# Language Translator Skill

## Purpose
Translate text between 100+ languages.

## When to Activate
Activate when the user asks to:
- translate to
- how do you say in
- translate <text>

## Core Workflows

Use LibreTranslate API or LLM-based translation for any language pair.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
