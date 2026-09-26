---
name: codegen-websocket-app
description: Generate real-time WebSocket application code.
---

# WebSocket App Generator Skill

## Purpose
Generate real-time WebSocket application code.

## When to Activate
Activate when the user asks to:
- WebSocket app
- real-time chat
- live updates code
- WebSocket server

## Core Workflows

Generate: FastAPI WebSocket server + JavaScript client with reconnect logic.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
