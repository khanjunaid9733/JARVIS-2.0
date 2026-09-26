---
name: db-connection-pool
description: Monitor active DB connections and pool utilization.
---

# Connection Pool Status Skill

## Purpose
Monitor active DB connections and pool utilization.

## When to Activate
Activate when the user asks to:
- DB connections
- pool status
- connection count

## Core Workflows

Query `pg_stat_activity` (PostgreSQL) or `SHOW PROCESSLIST` (MySQL).

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
