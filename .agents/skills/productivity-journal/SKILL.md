---
name: productivity-journal
description: Write and read personal journal entries with timestamps.
---

# Daily Journal Skill

## Purpose
Write and read personal journal entries with timestamps.

## When to Activate
Activate when the user asks to:
- journal entry
- daily log
- write in journal
- today's entry

## Core Workflows

Append dated entries to JARVIS_HOME/journal/<YYYY-MM-DD>.md.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
