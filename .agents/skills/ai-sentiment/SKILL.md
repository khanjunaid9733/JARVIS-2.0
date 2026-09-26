---
name: ai-sentiment
description: Analyze the sentiment (positive/negative/neutral) of any text.
---

# Sentiment Analyzer Skill

## Purpose
Analyze the sentiment (positive/negative/neutral) of any text.

## When to Activate
Activate when the user asks to:
- sentiment of
- is this positive
- analyze tone
- emotion in text

## Core Workflows

Prompt: `Rate the sentiment of the following as positive, negative, or neutral with confidence: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
