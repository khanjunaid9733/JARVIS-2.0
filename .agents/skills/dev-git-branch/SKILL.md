---
name: dev-git-branch
description: Create, list, switch, merge, and delete git branches.
---

# Git Branch Manager Skill

## Purpose
Create, list, switch, merge, and delete git branches.

## When to Activate
Activate when the user asks to:
- create branch
- switch branch
- list branches
- merge branch

## Core Workflows

```bash
git branch <name>; git checkout <name>; git merge <name>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
