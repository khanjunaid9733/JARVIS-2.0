---
name: pm-retrospective
description: Run a sprint retrospective with What Went Well / Didn't / Improve.
---

# Sprint Retrospective Skill

## Purpose
Run a sprint retrospective with What Went Well / Didn't / Improve.

## When to Activate
Activate when the user asks to:
- retrospective
- what went well
- sprint review
- lessons learned

## Core Workflows

Prompt: `Facilitate a sprint retrospective for {team}. Cover: What went well, What didn't, Action items.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
