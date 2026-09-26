---
name: photo-collage
description: Create image collages from multiple photos.
---

# Photo Collage Creator Skill

## Purpose
Create image collages from multiple photos.

## When to Activate
Activate when the user asks to:
- photo collage
- combine images
- image grid
- picture collage

## Core Workflows

Use PIL to create canvas, resize and paste images in grid layout.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
