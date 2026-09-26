---
name: photo-portrait-enhance
description: Apply AI-based portrait enhancement and skin smoothing.
---

# Portrait Enhancer Skill

## Purpose
Apply AI-based portrait enhancement and skin smoothing.

## When to Activate
Activate when the user asks to:
- enhance portrait
- skin smoothing
- portrait retouch
- improve photo

## Core Workflows

Use Real-ESRGAN for super-resolution or gfpgan for face restoration.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
