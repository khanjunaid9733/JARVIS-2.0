---
name: language-idiom-explain
description: Explain the meaning and origin of idioms and phrases.
---

# Idiom & Phrase Explainer Skill

## Purpose
Explain the meaning and origin of idioms and phrases.

## When to Activate
Activate when the user asks to:
- what does mean
- idiom
- phrase meaning
- expression

## Core Workflows

Prompt: `Explain the meaning, origin, and usage example for the idiom: '{idiom}'`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
