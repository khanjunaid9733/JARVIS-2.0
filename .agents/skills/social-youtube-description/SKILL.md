---
name: social-youtube-description
description: Write SEO-optimized YouTube video descriptions with chapters.
---

# YouTube Description Writer Skill

## Purpose
Write SEO-optimized YouTube video descriptions with chapters.

## When to Activate
Activate when the user asks to:
- YouTube description
- video description
- write video SEO

## Core Workflows

Prompt: `Write a YouTube description for a video about {topic} with SEO keywords and chapter markers.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
