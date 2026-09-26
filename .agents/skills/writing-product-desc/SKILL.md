---
name: writing-product-desc
description: Write compelling product descriptions for e-commerce listings.
---

# Product Description Writer Skill

## Purpose
Write compelling product descriptions for e-commerce listings.

## When to Activate
Activate when the user asks to:
- product description
- write for <product>
- ecommerce listing

## Core Workflows

Prompt: `Write a compelling product description for {product}. Highlight features, benefits, and target {audience}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
