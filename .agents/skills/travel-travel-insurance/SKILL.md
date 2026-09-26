---
name: travel-travel-insurance
description: Explain travel insurance options and recommend policies.
---

# Travel Insurance Advisor Skill

## Purpose
Explain travel insurance options and recommend policies.

## When to Activate
Activate when the user asks to:
- travel insurance
- trip insurance
- do I need insurance for trip

## Core Workflows

Prompt: `Recommend travel insurance coverage for a {destination} trip with activities: {activities}. Explain what's covered.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
