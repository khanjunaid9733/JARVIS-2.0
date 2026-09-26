---
name: netadmin-disk-usage
description: Find largest files and directories consuming disk space.
---

# Server Disk Usage Monitor Skill

## Purpose
Find largest files and directories consuming disk space.

## When to Activate
Activate when the user asks to:
- server disk space
- largest files
- du
- disk usage

## Core Workflows

```bash
du -sh /* | sort -rh | head -20
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
