---
name: db-restore
description: Restore a database from a backup file or snapshot.
---

# Database Restore Skill

## Purpose
Restore a database from a backup file or snapshot.

## When to Activate
Activate when the user asks to:
- restore database
- load backup
- restore from snapshot

## Core Workflows

```bash
psql -U user -d dbname < backup.sql
# or SQLite attach + copy
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
