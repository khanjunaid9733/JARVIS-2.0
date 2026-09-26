---
name: food-fermentation
description: Guide kombucha, kimchi, sourdough, and other fermentation projects.
---

# Fermentation Guide Skill

## Purpose
Guide kombucha, kimchi, sourdough, and other fermentation projects.

## When to Activate
Activate when the user asks to:
- fermentation
- kombucha
- kimchi
- sourdough starter
- ferment

## Core Workflows

Prompt: `Walk me through fermenting {item}: starter culture, temperature, timeline, troubleshooting.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
