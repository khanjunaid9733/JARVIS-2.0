---
name: language-literary-devices
description: Explain and identify literary devices in text.
---

# Literary Devices Explainer Skill

## Purpose
Explain and identify literary devices in text.

## When to Activate
Activate when the user asks to:
- literary device
- metaphor
- simile
- identify devices in text
- alliteration

## Core Workflows

Prompt: `Identify all literary devices in this text and explain each: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
