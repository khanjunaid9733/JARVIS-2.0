---
name: assistant-personal-bio
description: Store and recall personal information, preferences, and facts.
---

# Personal Info Manager Skill

## Purpose
Store and recall personal information, preferences, and facts.

## When to Activate
Activate when the user asks to:
- remember that I
- I prefer
- my address is
- personal info

## Core Workflows

Store as structured YAML in JARVIS_HOME/profile.yaml, recall on demand.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
