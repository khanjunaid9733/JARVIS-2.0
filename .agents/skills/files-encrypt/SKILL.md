---
name: files-encrypt
description: Encrypt files using AES-256-GCM symmetric encryption.
---

# File Encryption Skill

## Purpose
Encrypt files using AES-256-GCM symmetric encryption.

## When to Activate
Activate when the user asks to:
- encrypt <file>
- secure <file>
- lock <file>

## Core Workflows

Use `cryptography.hazmat.primitives.ciphers.aead.AESGCM` for authenticated encryption.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
