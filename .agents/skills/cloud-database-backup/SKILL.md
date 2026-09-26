---
name: cloud-database-backup
description: Trigger on-demand backup of RDS, Cloud SQL, or managed DB.
---

# Cloud Database Backup Skill

## Purpose
Trigger on-demand backup of RDS, Cloud SQL, or managed DB.

## When to Activate
Activate when the user asks to:
- backup database
- create DB snapshot
- cloud DB backup

## Core Workflows

Use AWS RDS `create_db_snapshot` or GCP SQL Admin API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
