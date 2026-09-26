---
name: language-text-statistics
description: Analyze text for word count, sentence length, Flesch reading ease.
---

# Text Statistics Analyzer Skill

## Purpose
Analyze text for word count, sentence length, Flesch reading ease.

## When to Activate
Activate when the user asks to:
- text stats
- readability
- word count
- reading level

## Core Workflows

Compute: word count, sentence count, avg sentence length, Flesch-Kincaid score.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
