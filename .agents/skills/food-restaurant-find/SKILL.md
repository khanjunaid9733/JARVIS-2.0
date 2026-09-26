---
name: food-restaurant-find
description: Find and rate restaurants near any location.
---

# Restaurant Finder Skill

## Purpose
Find and rate restaurants near any location.

## When to Activate
Activate when the user asks to:
- restaurants near
- good food in
- find restaurant
- where to eat

## Core Workflows

GET Google Places API `/nearbysearch` with type=restaurant and radius.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
