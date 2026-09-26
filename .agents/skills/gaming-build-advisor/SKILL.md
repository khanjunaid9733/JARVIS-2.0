---
name: gaming-build-advisor
description: Recommend PC components for a gaming build at a given budget.
---

# PC Build Advisor Skill

## Purpose
Recommend PC components for a gaming build at a given budget.

## When to Activate
Activate when the user asks to:
- PC build
- gaming PC
- build recommendation
- GPU recommendation

## Core Workflows

Prompt: `Recommend a {budget} gaming PC build for {use_case}. List CPU, GPU, RAM, storage, motherboard with prices.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
