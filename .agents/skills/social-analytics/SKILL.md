---
name: social-analytics
description: Pull engagement metrics (likes, comments, shares, impressions).
---

# Social Media Analytics Skill

## Purpose
Pull engagement metrics (likes, comments, shares, impressions).

## When to Activate
Activate when the user asks to:
- social media analytics
- engagement stats
- post performance

## Core Workflows

Query respective platform Analytics APIs for impressions, reach, engagement.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
