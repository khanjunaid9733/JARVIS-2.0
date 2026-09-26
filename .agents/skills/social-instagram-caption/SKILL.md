---
name: social-instagram-caption
description: Generate engaging captions and hashtag sets for Instagram posts.
---

# Instagram Caption Generator Skill

## Purpose
Generate engaging captions and hashtag sets for Instagram posts.

## When to Activate
Activate when the user asks to:
- Instagram caption
- write caption
- hashtags for <topic>

## Core Workflows

Prompt LLM: `Write 3 Instagram captions for a {topic} post with 10 relevant hashtags.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
