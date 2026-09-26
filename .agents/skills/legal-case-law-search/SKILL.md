---
name: legal-case-law-search
description: Search for relevant legal cases and precedents.
---

# Case Law Research Skill

## Purpose
Search for relevant legal cases and precedents.

## When to Activate
Activate when the user asks to:
- case law
- legal precedent
- court cases
- judicial decisions

## Core Workflows

Use CourtListener API or Caselaw Access Project API for case search.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
