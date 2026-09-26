---
name: media-meme-generate
description: Generate memes by overlaying text on template images.
---

# Meme Generator Skill

## Purpose
Generate memes by overlaying text on template images.

## When to Activate
Activate when the user asks to:
- make a meme
- create meme
- meme generator

## Core Workflows

Use PIL ImageDraw to render text on base meme image template.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
