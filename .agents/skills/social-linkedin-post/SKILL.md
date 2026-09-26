---
name: social-linkedin-post
description: Compose and publish professional posts to LinkedIn.
---

# LinkedIn Post Creator Skill

## Purpose
Compose and publish professional posts to LinkedIn.

## When to Activate
Activate when the user asks to:
- post to LinkedIn
- LinkedIn update
- share on LinkedIn

## Core Workflows

Use LinkedIn Share API: POST `/ugcPosts` with author and content.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
