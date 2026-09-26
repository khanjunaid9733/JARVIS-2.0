---
name: pm-status-report
description: Generate weekly project status reports with RAG indicators.
---

# Project Status Report Skill

## Purpose
Generate weekly project status reports with RAG indicators.

## When to Activate
Activate when the user asks to:
- status report
- project update
- weekly report
- RAG status

## Core Workflows

Prompt: `Write a project status report for {project} covering: Progress, Risks, Issues, Next Steps. Use RAG status.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
