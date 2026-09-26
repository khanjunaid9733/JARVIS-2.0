---
name: edu-concept-connect
description: Find and explain unexpected connections between disparate concepts.
---

# Concept Connector Skill

## Purpose
Find and explain unexpected connections between disparate concepts.

## When to Activate
Activate when the user asks to:
- how are these related
- connect concepts
- interdisciplinary
- link ideas

## Core Workflows

Prompt: `Explain the unexpected connections between {concept A} and {concept B}. Use examples.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
