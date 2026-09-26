---
name: browser-record-actions
description: Record user browser interactions and replay them.
---

# Browser Action Recorder Skill

## Purpose
Record user browser interactions and replay them.

## When to Activate
Activate when the user asks to:
- record browser
- record actions
- replay browser actions

## Core Workflows

Use Playwright's `codegen` mode or capture event sequences manually.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
