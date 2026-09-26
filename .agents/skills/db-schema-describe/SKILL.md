---
name: db-schema-describe
description: Describe tables, columns, and relationships in a database.
---

# Database Schema Inspector Skill

## Purpose
Describe tables, columns, and relationships in a database.

## When to Activate
Activate when the user asks to:
- describe schema
- list tables
- database structure
- what tables exist

## Core Workflows

Use INFORMATION_SCHEMA queries or SQLite `sqlite_master` table.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
