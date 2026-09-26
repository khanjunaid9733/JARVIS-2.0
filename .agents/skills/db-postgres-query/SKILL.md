---
name: db-postgres-query
description: Execute SQL queries against PostgreSQL databases.
---

# PostgreSQL Query Runner Skill

## Purpose
Execute SQL queries against PostgreSQL databases.

## When to Activate
Activate when the user asks to:
- query postgres
- run SQL on postgres
- postgres select

## Core Workflows

```python
import psycopg2; psycopg2.connect(dsn).cursor().execute(sql)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
