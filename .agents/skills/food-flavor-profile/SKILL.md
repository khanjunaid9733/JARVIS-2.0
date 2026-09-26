---
name: food-flavor-profile
description: Explain the flavor profile and seasoning approach for any cuisine.
---

# Flavor Profile Builder Skill

## Purpose
Explain the flavor profile and seasoning approach for any cuisine.

## When to Activate
Activate when the user asks to:
- flavor profile
- how to season
- spices for
- cuisine flavors

## Core Workflows

Prompt: `Describe the flavor profile of {cuisine}: key spices, aromatics, techniques, and classic pairings.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
