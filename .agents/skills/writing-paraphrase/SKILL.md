---
name: writing-paraphrase
description: Rewrite text to be unique while preserving the original meaning.
---

# Text Paraphraser Skill

## Purpose
Rewrite text to be unique while preserving the original meaning.

## When to Activate
Activate when the user asks to:
- paraphrase
- rewrite this
- rephrase
- make unique

## Core Workflows

Prompt: `Paraphrase the following text to be completely unique while preserving its meaning: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
