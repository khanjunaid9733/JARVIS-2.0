---
name: ds-report
description: Generate a full automated EDA report from a dataset.
---

# Data Analysis Report Skill

## Purpose
Generate a full automated EDA report from a dataset.

## When to Activate
Activate when the user asks to:
- full EDA report
- data report
- profiling report
- pandas profiling

## Core Workflows

Use `ydata-profiling` to generate interactive HTML report: `ProfileReport(df).to_file('report.html')`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
