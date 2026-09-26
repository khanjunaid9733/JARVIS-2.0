---
name: edu-explain-concept
description: Explain any concept in depth from beginner to expert level.
---

# Concept Explainer Skill

## Purpose
Explain any concept in depth from beginner to expert level.

## When to Activate
Activate when the user asks to:
- explain
- how does <X> work
- what is <topic>
- teach me about

## Core Workflows

Prompt: `Explain {concept} to someone at a {level} level. Use analogies and examples.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
