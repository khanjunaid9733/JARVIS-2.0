---
name: dev-git-log
description: Display commit history, authors, and diffs.
---

# Git Log Viewer Skill

## Purpose
Display commit history, authors, and diffs.

## When to Activate
Activate when the user asks to:
- git log
- show commit history
- recent commits

## Core Workflows

```bash
git -C <repo> log --oneline --graph -n 20
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
