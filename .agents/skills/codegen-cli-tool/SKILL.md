---
name: codegen-cli-tool
description: Generate command-line tools with argparse or Click.
---

# CLI Tool Generator Skill

## Purpose
Generate command-line tools with argparse or Click.

## When to Activate
Activate when the user asks to:
- CLI tool
- command line app
- argparse script
- Click CLI

## Core Workflows

Generate: argument parser, command handlers, help text, and error handling.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
