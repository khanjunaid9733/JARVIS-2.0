---
name: assistant-memory-log
description: Remember and recall key facts from conversations.
---

# Conversation Memory Log Skill

## Purpose
Remember and recall key facts from conversations.

## When to Activate
Activate when the user asks to:
- remember this
- recall what we discussed
- you mentioned
- save this

## Core Workflows

Commit facts to JARVIS durable memory with `remember:` prefix.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
