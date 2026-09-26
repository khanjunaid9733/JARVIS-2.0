---
name: ai-keyword-extract
description: Extract the most important keywords and phrases from any text.
---

# Keyword Extractor Skill

## Purpose
Extract the most important keywords and phrases from any text.

## When to Activate
Activate when the user asks to:
- extract keywords
- key topics in
- important terms in

## Core Workflows

Prompt: `Extract the 10 most important keywords and phrases from: {text}. Return as JSON list.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
