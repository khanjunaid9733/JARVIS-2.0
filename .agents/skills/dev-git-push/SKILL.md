---
name: dev-git-push
description: Push committed changes to the remote origin.
---

# Git Push Skill

## Purpose
Push committed changes to the remote origin.

## When to Activate
Activate when the user asks to:
- push to github
- git push
- upload commits

## Core Workflows

```bash
git -C <repo> push origin <branch>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
