---
name: cloud-log-query
description: Query application logs from CloudWatch Logs or GCP Logging.
---

# Cloud Log Query Skill

## Purpose
Query application logs from CloudWatch Logs or GCP Logging.

## When to Activate
Activate when the user asks to:
- query cloud logs
- CloudWatch logs
- GCP log search

## Core Workflows

Use AWS CloudWatch Logs Insights or GCP Logging API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
