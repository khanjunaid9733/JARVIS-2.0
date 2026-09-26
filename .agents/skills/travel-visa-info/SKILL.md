---
name: travel-visa-info
description: Find visa requirements for passport holders visiting any country.
---

# Visa Requirements Lookup Skill

## Purpose
Find visa requirements for passport holders visiting any country.

## When to Activate
Activate when the user asks to:
- visa for
- do I need visa
- visa requirements
- passport requirements

## Core Workflows

Use VisaDB API or Sherpa API for visa requirement data by passport+destination.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
