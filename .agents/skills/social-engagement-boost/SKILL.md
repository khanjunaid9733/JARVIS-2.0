---
name: social-engagement-boost
description: Recommend strategies to boost social media engagement.
---

# Engagement Strategy Advisor Skill

## Purpose
Recommend strategies to boost social media engagement.

## When to Activate
Activate when the user asks to:
- boost engagement
- grow followers
- increase reach

## Core Workflows

Prompt: `Recommend 10 specific strategies to boost {platform} engagement for {niche}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
