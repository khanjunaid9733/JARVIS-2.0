---
name: travel-hotel-search
description: Find and compare hotels in any city with price and ratings.
---

# Hotel Search Skill

## Purpose
Find and compare hotels in any city with price and ratings.

## When to Activate
Activate when the user asks to:
- find hotels
- hotel in <city>
- accommodation
- where to stay

## Core Workflows

Use Booking.com API or Amadeus Hotel Search API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
