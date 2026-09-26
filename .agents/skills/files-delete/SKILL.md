---
name: files-delete
description: Delete files or directories with optional recycle-bin safety.
---

# Delete File / Folder Skill

## Purpose
Delete files or directories with optional recycle-bin safety.

## When to Activate
Activate when the user asks to:
- delete file
- remove folder
- delete <path>

## Core Workflows

Use `send2trash` for safe deletion or `Path.unlink()` / `shutil.rmtree()`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
