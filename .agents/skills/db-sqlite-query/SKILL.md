---
name: db-sqlite-query
description: Run SQL queries on local SQLite databases.
---

# SQLite Query Runner Skill

## Purpose
Run SQL queries on local SQLite databases.

## When to Activate
Activate when the user asks to:
- query SQLite
- run SQL on local db
- sqlite select

## Core Workflows

```python
import sqlite3; conn = sqlite3.connect(path); conn.execute(sql).fetchall()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
