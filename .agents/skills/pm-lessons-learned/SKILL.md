---
name: pm-lessons-learned
description: Create a lessons learned document at project close.
---

# Lessons Learned Document Skill

## Purpose
Create a lessons learned document at project close.

## When to Activate
Activate when the user asks to:
- lessons learned
- project closure
- post-mortem
- what we learned

## Core Workflows

Prompt: `Write a lessons learned document for {project} covering: successes, failures, recommendations.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
