---
name: files-decrypt
description: Decrypt files encrypted with JARVIS AES-256-GCM.
---

# File Decryption Skill

## Purpose
Decrypt files encrypted with JARVIS AES-256-GCM.

## When to Activate
Activate when the user asks to:
- decrypt <file>
- unlock <file>

## Core Workflows

Use AESGCM.decrypt() with stored key and nonce.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
