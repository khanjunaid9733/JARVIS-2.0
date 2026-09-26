---
name: cloud-monitoring-alert
description: Set up alerts for CPU, memory, error rates via CloudWatch or GCP Monitoring.
---

# Cloud Monitoring Alert Skill

## Purpose
Set up alerts for CPU, memory, error rates via CloudWatch or GCP Monitoring.

## When to Activate
Activate when the user asks to:
- set cloud alert
- monitoring threshold
- CloudWatch alarm

## Core Workflows

Use AWS CloudWatch `put_metric_alarm` or GCP Monitoring API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
