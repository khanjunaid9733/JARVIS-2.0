---
name: cloud-scheduled-job
description: Create a cron job on AWS EventBridge or GCP Cloud Scheduler.
---

# Cloud Scheduled Job Creator Skill

## Purpose
Create a cron job on AWS EventBridge or GCP Cloud Scheduler.

## When to Activate
Activate when the user asks to:
- schedule cloud job
- create cron on AWS
- GCP Cloud Scheduler

## Core Workflows

Use AWS EventBridge rules or GCP Cloud Scheduler API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
