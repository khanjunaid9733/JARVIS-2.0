---
name: codegen-bash-script
description: Generate Bash/PowerShell automation scripts.
---

# Bash Script Generator Skill

## Purpose
Generate Bash/PowerShell automation scripts.

## When to Activate
Activate when the user asks to:
- Bash script
- shell script
- PowerShell script
- automation script

## Core Workflows

Generate: script with error handling, logging, argument parsing, and cleanup traps.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
