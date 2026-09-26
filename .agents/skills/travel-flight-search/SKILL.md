---
name: travel-flight-search
description: Search for available flights between cities with prices.
---

# Flight Search Skill

## Purpose
Search for available flights between cities with prices.

## When to Activate
Activate when the user asks to:
- find flights
- flight from to
- flight search
- cheapest flight

## Core Workflows

Use Skyscanner API or Amadeus Flight Offers Search API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
