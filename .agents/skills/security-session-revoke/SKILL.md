---
name: security-session-revoke
description: Revoke active API tokens, OAuth sessions, or kill active connections.
---

# Active Session Revoker Skill

## Purpose
Revoke active API tokens, OAuth sessions, or kill active connections.

## When to Activate
Activate when the user asks to:
- revoke session
- logout everywhere
- kill active sessions

## Core Workflows

Invoke `/revoke` or `/logout` endpoints of OAuth provider.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
