---
name: dev-git-pull
description: Pull latest changes from the remote repository.
---

# Git Pull Skill

## Purpose
Pull latest changes from the remote repository.

## When to Activate
Activate when the user asks to:
- git pull
- update repo
- fetch latest

## Core Workflows

```bash
git -C <repo> pull --rebase
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
