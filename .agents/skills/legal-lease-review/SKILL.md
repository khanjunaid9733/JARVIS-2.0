---
name: legal-lease-review
description: Identify key terms and risks in rental or commercial leases.
---

# Lease Agreement Reviewer Skill

## Purpose
Identify key terms and risks in rental or commercial leases.

## When to Activate
Activate when the user asks to:
- lease review
- rental agreement
- tenancy contract
- lease terms

## Core Workflows

Prompt: `Review this lease. Identify: term, rent escalation, exit clauses, tenant rights, unusual terms: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
