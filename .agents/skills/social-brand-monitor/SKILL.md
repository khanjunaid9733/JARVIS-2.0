---
name: social-brand-monitor
description: Track brand or keyword mentions across social platforms.
---

# Brand Mention Monitor Skill

## Purpose
Track brand or keyword mentions across social platforms.

## When to Activate
Activate when the user asks to:
- monitor brand
- track mentions
- social listening

## Core Workflows

Use Twitter Filtered Stream API or Mention/Brandwatch to track keyword occurrences.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
