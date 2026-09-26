---
name: codegen-python-script
description: Generate complete Python scripts from natural language specs.
---

# Python Script Generator Skill

## Purpose
Generate complete Python scripts from natural language specs.

## When to Activate
Activate when the user asks to:
- write Python script
- create Python program
- Python code for

## Core Workflows

Prompt: `Write a complete, runnable Python script that: {spec}. Include error handling and docstrings.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
