---
name: security-encrypt-text
description: Encrypt sensitive text using AES-256-GCM with a passphrase.
---

# Text Encryption Skill

## Purpose
Encrypt sensitive text using AES-256-GCM with a passphrase.

## When to Activate
Activate when the user asks to:
- encrypt text
- secure this message
- lock this data

## Core Workflows

Use PBKDF2 key derivation + AESGCM for authenticated encryption.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
