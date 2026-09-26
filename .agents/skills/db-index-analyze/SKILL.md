---
name: db-index-analyze
description: Identify missing indexes and query performance bottlenecks.
---

# Index Analyzer Skill

## Purpose
Identify missing indexes and query performance bottlenecks.

## When to Activate
Activate when the user asks to:
- analyze indexes
- slow query
- missing index
- query performance

## Core Workflows

Use `EXPLAIN ANALYZE` in PostgreSQL or `EXPLAIN QUERY PLAN` in SQLite.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
