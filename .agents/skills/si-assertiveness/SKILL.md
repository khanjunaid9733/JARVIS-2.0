---
name: si-assertiveness
description: Build assertiveness skills for difficult conversations.
---

# Assertiveness Trainer Skill

## Purpose
Build assertiveness skills for difficult conversations.

## When to Activate
Activate when the user asks to:
- be more assertive
- say no
- assertiveness
- difficult conversation

## Core Workflows

Prompt: `Coach me on being assertive in {situation}. Scripts for: setting boundaries, saying no, asking for needs.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
