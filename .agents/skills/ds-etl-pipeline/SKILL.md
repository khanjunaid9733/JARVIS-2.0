---
name: ds-etl-pipeline
description: Build extract-transform-load pipelines between data sources.
---

# ETL Pipeline Builder Skill

## Purpose
Build extract-transform-load pipelines between data sources.

## When to Activate
Activate when the user asks to:
- ETL pipeline
- data pipeline
- extract transform load
- move data from

## Core Workflows

Chain: source reader → transformer → validator → destination writer with retry logic.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
