---
name: netadmin-postgres-tune
description: Analyze and optimize PostgreSQL server configuration.
---

# PostgreSQL Performance Tuner Skill

## Purpose
Analyze and optimize PostgreSQL server configuration.

## When to Activate
Activate when the user asks to:
- postgres tuning
- PG config
- database slow
- optimize postgres

## Core Workflows

Check: `shared_buffers`, `work_mem`, `effective_cache_size`, slow query log, and VACUUM stats.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
