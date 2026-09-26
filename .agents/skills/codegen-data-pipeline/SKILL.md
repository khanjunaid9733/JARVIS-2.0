---
name: codegen-data-pipeline
description: Generate ETL data pipeline scripts.
---

# Data Pipeline Generator Skill

## Purpose
Generate ETL data pipeline scripts.

## When to Activate
Activate when the user asks to:
- data pipeline code
- ETL script
- data transformation script

## Core Workflows

Generate: source reader, transformer class, validator, and sink writer with retry logic.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
