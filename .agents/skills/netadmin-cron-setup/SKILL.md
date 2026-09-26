---
name: netadmin-cron-setup
description: Create, list, and remove cron jobs on Linux systems.
---

# Cron Job Manager Skill

## Purpose
Create, list, and remove cron jobs on Linux systems.

## When to Activate
Activate when the user asks to:
- add cron job
- list crons
- cron schedule
- crontab

## Core Workflows

Use `crontab -l` to list, `crontab -e` or echo-pipe to add jobs.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
