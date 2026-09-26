---
name: codegen-config-file
description: Generate config files for nginx, apache, systemd, etc.
---

# Config File Generator Skill

## Purpose
Generate config files for nginx, apache, systemd, etc.

## When to Activate
Activate when the user asks to:
- nginx config
- systemd service
- apache config
- config file for

## Core Workflows

Generate properly formatted config with best-practice security settings.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
