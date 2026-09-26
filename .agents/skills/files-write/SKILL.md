---
name: files-write
description: Atomically write content to any file on disk.
---

# Write File Skill

## Purpose
Atomically write content to any file on disk.

## When to Activate
Activate when the user asks to:
- write to file
- save as
- create file with

## Core Workflows

Use tempfile + os.replace for atomic write safety.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
