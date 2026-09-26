---
name: productivity-notes
description: Create, edit, search, and delete text notes.
---

# Note Taker Skill

## Purpose
Create, edit, search, and delete text notes.

## When to Activate
Activate when the user asks to:
- take a note
- save note
- write down
- my notes

## Core Workflows

Store notes as Markdown files in JARVIS_HOME/notes/ with ULID filenames.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
