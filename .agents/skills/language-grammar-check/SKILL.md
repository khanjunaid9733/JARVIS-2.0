---
name: language-grammar-check
description: Check and correct grammar, punctuation, and spelling.
---

# Grammar Checker Skill

## Purpose
Check and correct grammar, punctuation, and spelling.

## When to Activate
Activate when the user asks to:
- grammar check
- correct my English
- fix grammar
- spelling check

## Core Workflows

Use LanguageTool API or route through LLM for correction.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
