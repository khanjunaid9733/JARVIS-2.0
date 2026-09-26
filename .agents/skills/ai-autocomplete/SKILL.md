---
name: ai-autocomplete
description: Complete or extend any partial text, sentence, or paragraph.
---

# AI Text Autocomplete Skill

## Purpose
Complete or extend any partial text, sentence, or paragraph.

## When to Activate
Activate when the user asks to:
- continue this
- complete this sentence
- extend this paragraph

## Core Workflows

Prompt: `Continue the following text naturally: {partial_text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
