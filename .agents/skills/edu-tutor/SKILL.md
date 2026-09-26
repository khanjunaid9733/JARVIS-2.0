---
name: edu-tutor
description: Provide step-by-step tutoring on math, science, or humanities topics.
---

# AI Tutor Skill

## Purpose
Provide step-by-step tutoring on math, science, or humanities topics.

## When to Activate
Activate when the user asks to:
- tutor me
- help me understand
- walk me through
- practice with me

## Core Workflows

Interactive: present problem → guide with hints → check answer → explain solution.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
