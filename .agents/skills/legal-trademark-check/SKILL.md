---
name: legal-trademark-check
description: Check if a brand name or logo is trademarked.
---

# Trademark Availability Skill

## Purpose
Check if a brand name or logo is trademarked.

## When to Activate
Activate when the user asks to:
- trademark check
- is name trademarked
- brand name available

## Core Workflows

GET USPTO TESS API for trademark search by term.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
