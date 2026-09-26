---
name: pm-kpi-dashboard
description: Build a KPI tracking dashboard from project metrics.
---

# KPI Dashboard Skill

## Purpose
Build a KPI tracking dashboard from project metrics.

## When to Activate
Activate when the user asks to:
- KPI dashboard
- project metrics
- performance indicators
- track KPIs

## Core Workflows

Aggregate KPI data sources, compute target vs actual, generate table/chart.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
