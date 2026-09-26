---
name: social-competitor-analysis
description: Analyze a competitor's social media strategy and content.
---

# Competitor Social Analysis Skill

## Purpose
Analyze a competitor's social media strategy and content.

## When to Activate
Activate when the user asks to:
- competitor analysis
- what does <brand> post
- analyze <competitor>

## Core Workflows

Fetch public posts via platform APIs, analyze themes, frequency, engagement.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
