---
name: edu-mind-map
description: Generate structured mind maps for complex topics.
---

# Mind Map Creator Skill

## Purpose
Generate structured mind maps for complex topics.

## When to Activate
Activate when the user asks to:
- mind map
- concept map
- visual outline
- brainstorm structure

## Core Workflows

Prompt: `Create a hierarchical mind map for {topic} with main branches and sub-concepts.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
