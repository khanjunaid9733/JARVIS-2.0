---
name: social-twitter-post
description: Compose and schedule posts for Twitter/X.
---

# Twitter / X Post Creator Skill

## Purpose
Compose and schedule posts for Twitter/X.

## When to Activate
Activate when the user asks to:
- tweet
- post to Twitter
- schedule tweet
- X post

## Core Workflows

Use Twitter API v2: POST `/2/tweets` with text payload.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
