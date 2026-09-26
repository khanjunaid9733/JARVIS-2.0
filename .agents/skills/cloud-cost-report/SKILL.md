---
name: cloud-cost-report
description: Fetch and summarize cloud spending by service and time period.
---

# Cloud Cost Report Skill

## Purpose
Fetch and summarize cloud spending by service and time period.

## When to Activate
Activate when the user asks to:
- cloud costs
- AWS spending
- how much am I spending on cloud

## Core Workflows

Use AWS Cost Explorer API or GCP Billing API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
