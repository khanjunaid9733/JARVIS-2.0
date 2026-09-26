---
name: social-story-ideas
description: Generate Instagram/Snapchat story content ideas for a brand.
---

# Story Ideas Generator Skill

## Purpose
Generate Instagram/Snapchat story content ideas for a brand.

## When to Activate
Activate when the user asks to:
- story ideas
- Instagram stories
- content for stories

## Core Workflows

Prompt: `Generate 20 engaging Instagram story ideas for a {brand/niche} to post this week.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
