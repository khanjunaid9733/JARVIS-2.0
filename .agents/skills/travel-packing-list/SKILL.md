---
name: travel-packing-list
description: Generate smart packing lists based on destination, duration, and activities.
---

# Packing List Generator Skill

## Purpose
Generate smart packing lists based on destination, duration, and activities.

## When to Activate
Activate when the user asks to:
- packing list
- what to pack
- travel checklist
- pack for <trip>

## Core Workflows

Prompt: `Create a comprehensive packing list for a {days}-day trip to {destination} in {season} for {activities}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
