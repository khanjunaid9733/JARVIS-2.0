---
name: ai-image-describe
description: Generate a textual description of any image using vision LLM.
---

# AI Image Description Skill

## Purpose
Generate a textual description of any image using vision LLM.

## When to Activate
Activate when the user asks to:
- describe this image
- what's in this picture
- analyze image

## Core Workflows

Route image through VisionModelAdapter with `describe_image` instruction.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
