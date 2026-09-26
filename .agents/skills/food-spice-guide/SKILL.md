---
name: food-spice-guide
description: Explain the flavor, uses, and health benefits of any spice.
---

# Spice Encyclopedia Skill

## Purpose
Explain the flavor, uses, and health benefits of any spice.

## When to Activate
Activate when the user asks to:
- what is
- spice guide
- flavor of
- health benefits of spice

## Core Workflows

Prompt: `Describe {spice}: flavor profile, cuisines that use it, cooking tips, and health properties.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
