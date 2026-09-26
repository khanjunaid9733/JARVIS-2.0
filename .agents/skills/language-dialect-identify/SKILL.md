---
name: language-dialect-identify
description: Identify regional dialects and explain key features.
---

# Dialect & Accent Identifier Skill

## Purpose
Identify regional dialects and explain key features.

## When to Activate
Activate when the user asks to:
- what dialect
- accent identify
- regional speech
- English dialect

## Core Workflows

Prompt: `Analyze and identify the dialect features in: {text}. Explain regional and cultural markers.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
