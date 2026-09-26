---
name: sysdiag-report
description: Generate a complete system health snapshot across all metrics.
---

# Full System Health Report Skill

## Purpose
Generate a complete system health snapshot across all metrics.

## When to Activate
Activate when the user asks to:
- system health report
- full diagnostics
- PC status report

## Core Workflows

Aggregate CPU, RAM, disk, temp, battery, network, and processes into a JSON report.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
