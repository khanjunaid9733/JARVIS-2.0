---
name: science-astronomy
description: Look up planet positions, star data, and astronomical events.
---

# Astronomy Data Fetcher Skill

## Purpose
Look up planet positions, star data, and astronomical events.

## When to Activate
Activate when the user asks to:
- planet position
- star data
- when is lunar eclipse
- astronomy

## Core Workflows

Use NASA API or Astropy library for celestial mechanics data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
