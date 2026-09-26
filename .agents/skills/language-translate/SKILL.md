---
name: language-translate
description: Translate text between 100+ languages with context preservation.
---

# Multi-Language Translator Skill

## Purpose
Translate text between 100+ languages with context preservation.

## When to Activate
Activate when the user asks to:
- translate
- how do you say
- translate to
- in Spanish
- in French

## Core Workflows

Use LibreTranslate, DeepL, or LLM: `Translate to {lang}: {text}`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
