---
name: travel-food-guide
description: Discover must-try local dishes and food culture at any destination.
---

# Local Food Guide Skill

## Purpose
Discover must-try local dishes and food culture at any destination.

## When to Activate
Activate when the user asks to:
- local food in
- what to eat in
- cuisine guide
- food culture

## Core Workflows

Prompt: `Give a food guide for {city/country}: top 10 dishes, best street food areas, food customs.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
