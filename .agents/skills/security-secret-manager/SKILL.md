---
name: security-secret-manager
description: Store and retrieve API keys and secrets from an encrypted vault.
---

# Secret / Key Manager Skill

## Purpose
Store and retrieve API keys and secrets from an encrypted vault.

## When to Activate
Activate when the user asks to:
- store secret
- retrieve API key
- save credential
- vault

## Core Workflows

Use JARVIS encrypted vault backed by AESGCM + Ed25519 creator authority.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
