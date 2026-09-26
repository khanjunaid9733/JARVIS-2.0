---
name: ai-classify
description: Classify text into categories using zero-shot LLM classification.
---

# AI Text Classifier Skill

## Purpose
Classify text into categories using zero-shot LLM classification.

## When to Activate
Activate when the user asks to:
- classify this
- categorize
- what type is this
- label

## Core Workflows

Prompt: `Classify the following into [categories]: {text}. Respond with one label.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
