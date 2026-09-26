---
name: dev-git-status
description: Check the current git status of any repository.
---

# Git Status Skill

## Purpose
Check the current git status of any repository.

## When to Activate
Activate when the user asks to:
- git status
- what's changed
- show uncommitted changes

## Core Workflows

```bash
git -C <repo> status
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
