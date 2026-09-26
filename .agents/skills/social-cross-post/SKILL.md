---
name: social-cross-post
description: Publish one post simultaneously across all social platforms.
---

# Cross-Platform Publisher Skill

## Purpose
Publish one post simultaneously across all social platforms.

## When to Activate
Activate when the user asks to:
- cross-post
- publish everywhere
- share across all platforms

## Core Workflows

Invoke all platform posting skills in parallel with unified content.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
