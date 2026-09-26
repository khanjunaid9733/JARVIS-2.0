---
name: marketing-email-sequence
description: Write automated email sequences for onboarding, nurture, or sales.
---

# Email Marketing Sequence Skill

## Purpose
Write automated email sequences for onboarding, nurture, or sales.

## When to Activate
Activate when the user asks to:
- email sequence
- drip campaign
- onboarding emails
- nurture sequence

## Core Workflows

Generate 5-7 email sequence: welcome → value → social proof → offer → follow-up.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
