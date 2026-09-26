---
name: travel-itinerary
description: Create day-by-day travel itineraries for any destination.
---

# Travel Itinerary Builder Skill

## Purpose
Create day-by-day travel itineraries for any destination.

## When to Activate
Activate when the user asks to:
- travel plan
- itinerary for
- trip to <destination>
- plan my trip

## Core Workflows

Prompt: `Create a {days}-day itinerary for {destination} including must-see attractions, restaurants, and daily schedule.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
