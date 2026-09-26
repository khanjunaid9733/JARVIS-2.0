---
name: assistant-personal-shopper
description: Find and compare product deals across online stores.
---

# Personal Shopping Assistant Skill

## Purpose
Find and compare product deals across online stores.

## When to Activate
Activate when the user asks to:
- find me
- buy <product>
- best deal on
- where to buy

## Core Workflows

Search Google Shopping API or Amazon Product Advertising API for best deals.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
