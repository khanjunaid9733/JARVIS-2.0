---
name: pm-stakeholder-update
description: Draft executive-level stakeholder updates and summaries.
---

# Stakeholder Update Skill

## Purpose
Draft executive-level stakeholder updates and summaries.

## When to Activate
Activate when the user asks to:
- stakeholder update
- executive summary
- management report
- board update

## Core Workflows

Prompt: `Write a concise executive stakeholder update for {project}. Focus on outcomes, risks, and decisions needed.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
