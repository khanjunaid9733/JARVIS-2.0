---
name: legal-court-filing
description: Explain court filing procedures and required documents.
---

# Court Filing Guide Skill

## Purpose
Explain court filing procedures and required documents.

## When to Activate
Activate when the user asks to:
- file in court
- court procedure
- filing deadline
- court documents

## Core Workflows

Prompt: `Explain how to file {case_type} in {jurisdiction} court. List required documents and steps.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
