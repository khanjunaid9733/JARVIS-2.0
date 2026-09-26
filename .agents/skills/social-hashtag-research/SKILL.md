---
name: social-hashtag-research
description: Find the best performing hashtags for any topic.
---

# Hashtag Research Skill

## Purpose
Find the best performing hashtags for any topic.

## When to Activate
Activate when the user asks to:
- hashtag research
- best hashtags for
- trending hashtags

## Core Workflows

Use RiteTag or Hashtagify APIs, or query Twitter Trending Topics API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
