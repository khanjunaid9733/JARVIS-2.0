---
name: db-migrate
description: Apply schema migrations using Alembic or custom SQL files.
---

# Database Migration Runner Skill

## Purpose
Apply schema migrations using Alembic or custom SQL files.

## When to Activate
Activate when the user asks to:
- run migrations
- apply schema changes
- upgrade database

## Core Workflows

```bash
alembic upgrade head
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
