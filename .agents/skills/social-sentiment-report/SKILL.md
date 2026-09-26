---
name: social-sentiment-report
description: Analyze public sentiment about a topic across Twitter/Reddit.
---

# Social Sentiment Report Skill

## Purpose
Analyze public sentiment about a topic across Twitter/Reddit.

## When to Activate
Activate when the user asks to:
- social sentiment
- how people feel about
- public opinion on

## Core Workflows

Fetch recent posts, run sentiment classifier, aggregate scores by day.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
