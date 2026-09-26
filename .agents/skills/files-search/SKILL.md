---
name: files-search
description: Find files matching patterns, names, content, or modification dates.
---

# File Search Skill

## Purpose
Find files matching patterns, names, content, or modification dates.

## When to Activate
Activate when the user asks to:
- find files named
- search for files containing
- files modified today

## Core Workflows

Use `glob.glob()` with `recursive=True` or `os.walk()` with filters.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
