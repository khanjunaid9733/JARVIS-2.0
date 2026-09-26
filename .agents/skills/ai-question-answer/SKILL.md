---
name: ai-question-answer
description: Answer any factual question using LLM knowledge or retrieved context.
---

# AI Question Answering Skill

## Purpose
Answer any factual question using LLM knowledge or retrieved context.

## When to Activate
Activate when the user asks to:
- what is
- how does
- explain
- when did
- why does

## Core Workflows

Use model-backed `answer_question()` path in JARVIS kernel.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
