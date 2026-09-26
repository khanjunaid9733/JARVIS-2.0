---
name: productivity-read-later
description: Save articles and URLs for later reading.
---

# Read-Later Queue Skill

## Purpose
Save articles and URLs for later reading.

## When to Activate
Activate when the user asks to:
- save for later
- add to reading list
- read later

## Core Workflows

Append URL + title + summary to JARVIS_HOME/read_later.json.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
