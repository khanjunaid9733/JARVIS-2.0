---
name: ai-summarize
description: Summarize any text, document, or article using the LLM.
---

# AI Text Summarizer Skill

## Purpose
Summarize any text, document, or article using the LLM.

## When to Activate
Activate when the user asks to:
- summarize
- tldr
- shorten this
- condense

## Core Workflows

Chunk text to fit context window, route to LLM with `summarize_text` instruction.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
