---
name: health-meditation
description: Guide users through timed breathing and meditation sessions.
---

# Meditation Guide Skill

## Purpose
Guide users through timed breathing and meditation sessions.

## When to Activate
Activate when the user asks to:
- meditate
- breathing exercise
- guided meditation
- calm down

## Core Workflows

Box breathing: inhale 4s → hold 4s → exhale 4s → hold 4s. Loop with TTS guidance.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
