---
name: legal-employment-law
description: Provide information on employment law topics.
---

# Employment Law Advisor Skill

## Purpose
Provide information on employment law topics.

## When to Activate
Activate when the user asks to:
- employment law
- wrongful termination
- discrimination law
- labor rights

## Core Workflows

Prompt: `Explain {employment_topic} under {jurisdiction} law. Include rights, obligations, and limitations.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
