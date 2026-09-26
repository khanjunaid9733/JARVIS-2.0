---
name: marketing-a-b-test
description: Design A/B test experiments for landing pages or emails.
---

# A/B Test Designer Skill

## Purpose
Design A/B test experiments for landing pages or emails.

## When to Activate
Activate when the user asks to:
- A/B test
- split test
- test variant
- experiment design

## Core Workflows

Define: hypothesis, variants, metric, sample size, duration, success criteria.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
