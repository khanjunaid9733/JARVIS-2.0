---
name: health-symptom-check
description: Provide general information about symptoms and when to see a doctor.
---

# Symptom Checker Skill

## Purpose
Provide general information about symptoms and when to see a doctor.

## When to Activate
Activate when the user asks to:
- symptom
- I feel
- what causes
- should I see a doctor

## Core Workflows

Prompt: `Provide general information (not medical advice) about these symptoms: {symptoms}. Include red flags.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
