---
name: db-seed
description: Populate a database with seed/test data from JSON or CSV files.
---

# Database Seeder Skill

## Purpose
Populate a database with seed/test data from JSON or CSV files.

## When to Activate
Activate when the user asks to:
- seed database
- load test data
- import data into db

## Core Workflows

Parse seed file, batch-insert records using appropriate connector.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
