---
name: db-change-stream
description: Subscribe to MongoDB or PostgreSQL change streams for real-time updates.
---

# Database Change Stream Skill

## Purpose
Subscribe to MongoDB or PostgreSQL change streams for real-time updates.

## When to Activate
Activate when the user asks to:
- watch DB changes
- change stream
- realtime DB updates

## Core Workflows

Use `collection.watch()` (MongoDB) or PostgreSQL logical replication / LISTEN/NOTIFY.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
