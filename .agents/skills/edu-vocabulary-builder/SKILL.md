---
name: edu-vocabulary-builder
description: Build vocabulary lists with definitions, examples, and etymology.
---

# Vocabulary Builder Skill

## Purpose
Build vocabulary lists with definitions, examples, and etymology.

## When to Activate
Activate when the user asks to:
- vocabulary
- word meanings
- define these words
- etymology

## Core Workflows

Prompt: `For each word in [{words}], provide: definition, part of speech, 2 example sentences, etymology.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
