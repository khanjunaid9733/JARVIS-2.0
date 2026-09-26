---
name: codegen-sql-query
description: Generate SQL queries from natural language questions.
---

# SQL Query Generator Skill

## Purpose
Generate SQL queries from natural language questions.

## When to Activate
Activate when the user asks to:
- write SQL
- query for
- SQL to
- generate SQL query

## Core Workflows

Prompt: `Write an efficient {db_type} SQL query to: {requirement}. Tables: {schema}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
