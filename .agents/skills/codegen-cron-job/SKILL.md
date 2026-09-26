---
name: codegen-cron-job
description: Generate scheduled job scripts with logging and error handling.
---

# Cron Job Code Generator Skill

## Purpose
Generate scheduled job scripts with logging and error handling.

## When to Activate
Activate when the user asks to:
- cron job
- scheduled script
- background job
- recurring task code

## Core Workflows

Generate: Python script + systemd timer or crontab entry with logging config.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
