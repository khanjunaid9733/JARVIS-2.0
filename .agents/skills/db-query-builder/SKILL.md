---
name: db-query-builder
description: Convert a natural language question to an SQL query using LLM.
---

# Natural Language SQL Skill

## Purpose
Convert a natural language question to an SQL query using LLM.

## When to Activate
Activate when the user asks to:
- SQL for <question>
- query in plain english
- write SQL that

## Core Workflows

Prompt: `Write a SQL query for: {question}. Tables available: {schema}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
