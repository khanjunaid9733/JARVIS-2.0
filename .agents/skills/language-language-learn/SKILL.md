---
name: language-language-learn
description: Teach phrases, vocabulary, and grammar for any language.
---

# Language Learning Coach Skill

## Purpose
Teach phrases, vocabulary, and grammar for any language.

## When to Activate
Activate when the user asks to:
- teach me
- learn <language>
- Spanish lesson
- French vocabulary

## Core Workflows

Prompt: `Teach me {topic} in {language}. Give examples, pronunciation guide, and practice exercise.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
