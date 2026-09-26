---
name: codegen-database-schema
description: Design and generate SQL database schemas from requirements.
---

# Database Schema Generator Skill

## Purpose
Design and generate SQL database schemas from requirements.

## When to Activate
Activate when the user asks to:
- database design
- create schema
- ER diagram
- DB tables for

## Core Workflows

Generate: CREATE TABLE statements, indexes, foreign keys, and normalization comments.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
