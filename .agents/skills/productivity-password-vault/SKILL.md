---
name: productivity-password-vault
description: Securely store and retrieve passwords and credentials.
---

# Password Vault Skill

## Purpose
Securely store and retrieve passwords and credentials.

## When to Activate
Activate when the user asks to:
- save password
- get password for
- credential vault

## Core Workflows

Encrypt entries with AESGCM key derived from creator key, store in JARVIS_HOME/vault.enc.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
