---
name: security-hash-file
description: Compute and verify file hashes to detect tampering.
---

# File Integrity Checker Skill

## Purpose
Compute and verify file hashes to detect tampering.

## When to Activate
Activate when the user asks to:
- verify file integrity
- check file hash
- file checksum

## Core Workflows

SHA256 of file bytes, compare to known-good stored hash.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
