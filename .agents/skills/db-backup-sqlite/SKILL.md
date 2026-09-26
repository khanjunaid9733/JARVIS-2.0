---
name: db-backup-sqlite
description: Create online backup copies of SQLite database files.
---

# SQLite Backup Skill

## Purpose
Create online backup copies of SQLite database files.

## When to Activate
Activate when the user asks to:
- backup database
- backup SQLite
- DB snapshot

## Core Workflows

```python
conn.backup(sqlite3.connect(backup_path))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
