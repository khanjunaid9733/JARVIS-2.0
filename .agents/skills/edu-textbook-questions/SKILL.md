---
name: edu-textbook-questions
description: Generate comprehension and critical thinking questions for any text.
---

# Comprehension Questions Skill

## Purpose
Generate comprehension and critical thinking questions for any text.

## When to Activate
Activate when the user asks to:
- questions about
- comprehension check
- critical thinking questions

## Core Workflows

Prompt: `Generate 10 comprehension questions and 5 critical thinking questions for this text: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
