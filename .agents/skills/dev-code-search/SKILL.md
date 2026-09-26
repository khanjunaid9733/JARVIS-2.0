---
name: dev-code-search
description: Search for patterns, function definitions, or TODO comments in code.
---

# Code Search Skill

## Purpose
Search for patterns, function definitions, or TODO comments in code.

## When to Activate
Activate when the user asks to:
- search code for
- find function
- where is <pattern>
- list TODOs

## Core Workflows

Use ripgrep: `rg '<pattern>' --type py -n`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
