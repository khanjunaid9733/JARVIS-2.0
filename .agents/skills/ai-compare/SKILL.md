---
name: ai-compare
description: Compare two items, technologies, approaches, or documents.
---

# AI Comparison Analyzer Skill

## Purpose
Compare two items, technologies, approaches, or documents.

## When to Activate
Activate when the user asks to:
- compare <A> vs <B>
- difference between
- which is better

## Core Workflows

Prompt: `Compare {A} and {B} across: features, pros, cons, use cases. Return a structured table.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
