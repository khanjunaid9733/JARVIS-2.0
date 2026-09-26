---
name: media-generate-image
description: Generate images from text prompts using DALL-E or Stable Diffusion.
---

# AI Image Generator Skill

## Purpose
Generate images from text prompts using DALL-E or Stable Diffusion.

## When to Activate
Activate when the user asks to:
- generate image
- create picture of
- draw <description>
- image of

## Core Workflows

POST to OpenAI `/images/generations` or local Stable Diffusion API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
