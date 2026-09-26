---
name: ai-chat
description: Start a multi-turn conversational session with any LLM.
---

# AI Chat Session Skill

## Purpose
Start a multi-turn conversational session with any LLM.

## When to Activate
Activate when the user asks to:
- talk to AI
- chat mode
- ask AI
- converse

## Core Workflows

Route through ModelGateway with message history, track turns in episodic memory.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
