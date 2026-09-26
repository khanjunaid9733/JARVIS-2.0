---
name: writing-abstract
description: Write academic abstracts for research papers.
---

# Research Abstract Writer Skill

## Purpose
Write academic abstracts for research papers.

## When to Activate
Activate when the user asks to:
- write abstract
- research summary
- paper abstract

## Core Workflows

Prompt: `Write a 200-word academic abstract for a paper about: {topic}. Include objective, method, results, conclusions.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
