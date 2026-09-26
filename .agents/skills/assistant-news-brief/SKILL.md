---
name: assistant-news-brief
description: Deliver a curated news summary on selected topics.
---

# Personalized News Brief Skill

## Purpose
Deliver a curated news summary on selected topics.

## When to Activate
Activate when the user asks to:
- news update
- what's happening
- latest news
- news brief

## Core Workflows

Fetch RSS feeds from configured news sources, summarize top stories.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
