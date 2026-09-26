---
name: marketing-ad-copy
description: Write high-converting ad copy for Google, Facebook, or LinkedIn.
---

# Ad Copy Writer Skill

## Purpose
Write high-converting ad copy for Google, Facebook, or LinkedIn.

## When to Activate
Activate when the user asks to:
- write ad
- ad copy
- marketing copy
- headline for ad

## Core Workflows

Prompt: `Write 5 {platform} ad variations for {product} targeting {audience}. Include headline, description, CTA.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
