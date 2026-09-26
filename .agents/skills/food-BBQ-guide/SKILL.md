---
name: food-BBQ-guide
description: Guide for BBQ temperatures, times, and techniques.
---

# BBQ & Grilling Guide Skill

## Purpose
Guide for BBQ temperatures, times, and techniques.

## When to Activate
Activate when the user asks to:
- BBQ guide
- grill temperature
- smoking time
- BBQ technique

## Core Workflows

Prompt: `What are the optimal temperature and technique for grilling/smoking {meat} to {doneness}?`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
