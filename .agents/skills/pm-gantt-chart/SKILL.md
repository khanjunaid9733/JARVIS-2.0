---
name: pm-gantt-chart
description: Generate Gantt charts from project task lists.
---

# Gantt Chart Generator Skill

## Purpose
Generate Gantt charts from project task lists.

## When to Activate
Activate when the user asks to:
- Gantt chart
- project timeline visual
- task timeline

## Core Workflows

Use plotly or matplotlib to render Gantt chart from task/start/end data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
