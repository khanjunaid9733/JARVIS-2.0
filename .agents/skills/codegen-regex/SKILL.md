---
name: codegen-regex
description: Generate regular expressions for any pattern matching requirement.
---

# Regex Generator Skill

## Purpose
Generate regular expressions for any pattern matching requirement.

## When to Activate
Activate when the user asks to:
- regex for
- regular expression
- match pattern
- validate format

## Core Workflows

Prompt: `Generate a regular expression that matches: {pattern_description}. Explain each part.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
