---
name: cloud-health-check
description: Check the health/status of cloud provider services.
---

# Cloud Service Health Check Skill

## Purpose
Check the health/status of cloud provider services.

## When to Activate
Activate when the user asks to:
- is AWS down
- GCP status
- cloud health

## Core Workflows

GET `https://status.aws.amazon.com/data.json` or cloud status page API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
