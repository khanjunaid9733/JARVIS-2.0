---
name: dev-git-commit
description: Stage all changes and create a git commit with a message.
---

# Git Commit Skill

## Purpose
Stage all changes and create a git commit with a message.

## When to Activate
Activate when the user asks to:
- commit changes
- git commit
- save changes to git

## Core Workflows

```bash
git -C <repo> add -A && git commit -m '<message>'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
