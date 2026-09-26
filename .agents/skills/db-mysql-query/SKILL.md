---
name: db-mysql-query
description: Execute SQL queries against MySQL databases.
---

# MySQL Query Runner Skill

## Purpose
Execute SQL queries against MySQL databases.

## When to Activate
Activate when the user asks to:
- query MySQL
- run SQL on MySQL
- mysql select

## Core Workflows

```python
import mysql.connector; mysql.connector.connect(**config).cursor().execute(sql)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
