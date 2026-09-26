---
name: ai-essay-write
description: Write complete essays, reports, memos, and structured documents.
---

# AI Essay / Document Writer Skill

## Purpose
Write complete essays, reports, memos, and structured documents.

## When to Activate
Activate when the user asks to:
- write an essay about
- draft a report on
- create a document about

## Core Workflows

Prompt: `Write a well-structured {format} about {topic}. Use headings and examples.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
