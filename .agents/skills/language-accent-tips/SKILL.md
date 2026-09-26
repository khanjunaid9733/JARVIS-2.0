---
name: language-accent-tips
description: Provide tips for reducing or acquiring a specific accent.
---

# Accent Reduction Tips Skill

## Purpose
Provide tips for reducing or acquiring a specific accent.

## When to Activate
Activate when the user asks to:
- accent help
- sound more native
- accent training
- pronunciation practice

## Core Workflows

Prompt: `Give 10 specific tips for a {native_lang} speaker to reduce their accent in {target_lang}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
