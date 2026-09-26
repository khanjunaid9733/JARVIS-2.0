---
name: social-reddit-post
description: Create Reddit posts and find the best subreddit to post in.
---

# Reddit Post Creator Skill

## Purpose
Create Reddit posts and find the best subreddit to post in.

## When to Activate
Activate when the user asks to:
- post to Reddit
- submit to Reddit
- Reddit post

## Core Workflows

Use Reddit API: POST `/api/submit` via OAuth2 with subreddit, title, body.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
