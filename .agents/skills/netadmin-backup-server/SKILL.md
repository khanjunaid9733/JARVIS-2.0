---
name: netadmin-backup-server
description: Run rsync backups of server directories to remote or S3.
---

# Server Backup Orchestrator Skill

## Purpose
Run rsync backups of server directories to remote or S3.

## When to Activate
Activate when the user asks to:
- backup server
- rsync backup
- server backup

## Core Workflows

```bash
rsync -avz --delete /src/ user@remote:/backup/ --exclude='*.tmp'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
