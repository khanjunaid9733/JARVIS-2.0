---
name: language-false-friends
description: Identify and explain false cognates between languages.
---

# False Friends Guide Skill

## Purpose
Identify and explain false cognates between languages.

## When to Activate
Activate when the user asks to:
- false friends
- same word different meaning
- cognate
- similar but different

## Core Workflows

Prompt: `List 10 false friends between {lang1} and {lang2} with their correct meanings and examples.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
