---
name: social-influencer-find
description: Find influencers in a niche by follower count and engagement rate.
---

# Influencer Finder Skill

## Purpose
Find influencers in a niche by follower count and engagement rate.

## When to Activate
Activate when the user asks to:
- find influencers
- influencer research
- who to collaborate with

## Core Workflows

Use HypeAuditor or Instagram Graph API to search by hashtag and category.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
