---
name: ai-code-gen
description: Generate code in any programming language from a natural language spec.
---

# AI Code Generator Skill

## Purpose
Generate code in any programming language from a natural language spec.

## When to Activate
Activate when the user asks to:
- write code for
- generate Python script
- create function that
- code this

## Core Workflows

Prompt: `Write {language} code that: {spec}. Return only the code block.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
