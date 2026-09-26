---
name: edu-summarize-textbook
description: Summarize chapters or entire textbooks into key points.
---

# Textbook Summarizer Skill

## Purpose
Summarize chapters or entire textbooks into key points.

## When to Activate
Activate when the user asks to:
- summarize chapter
- textbook summary
- key points from

## Core Workflows

Chunk text by chapter, summarize each, compile into hierarchical outline.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
