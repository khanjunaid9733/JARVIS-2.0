---
name: travel-local-attractions
description: Find top-rated restaurants, museums, and attractions near any location.
---

# Local Attractions Finder Skill

## Purpose
Find top-rated restaurants, museums, and attractions near any location.

## When to Activate
Activate when the user asks to:
- what to do in
- things to see in
- restaurants near
- local attractions

## Core Workflows

GET Google Places API `/nearbysearch` or Foursquare Places API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
