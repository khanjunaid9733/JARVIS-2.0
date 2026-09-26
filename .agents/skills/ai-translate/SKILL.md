---
name: ai-translate
description: Translate text between any language pair using the LLM.
---

# AI Text Translator Skill

## Purpose
Translate text between any language pair using the LLM.

## When to Activate
Activate when the user asks to:
- translate to
- translate from
- convert language

## Core Workflows

Prompt: `Translate the following to {target_language}: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
