---
name: files-watcher
description: Watch a directory for create, modify, delete, rename events.
---

# File System Watcher Skill

## Purpose
Watch a directory for create, modify, delete, rename events.

## When to Activate
Activate when the user asks to:
- watch folder
- monitor directory
- alert on file change

## Core Workflows

Use `watchdog` Python library: `Observer().schedule(handler, path, recursive=True)`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
