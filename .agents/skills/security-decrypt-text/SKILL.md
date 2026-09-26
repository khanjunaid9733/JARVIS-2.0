---
name: security-decrypt-text
description: Decrypt text encrypted with JARVIS AES-256-GCM.
---

# Text Decryption Skill

## Purpose
Decrypt text encrypted with JARVIS AES-256-GCM.

## When to Activate
Activate when the user asks to:
- decrypt text
- unlock message

## Core Workflows

Reverse PBKDF2 + AESGCM decryption with stored salt and nonce.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
