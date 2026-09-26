---
name: ai-format-data
description: Convert unstructured text into structured JSON, tables, or YAML.
---

# AI Data Formatter Skill

## Purpose
Convert unstructured text into structured JSON, tables, or YAML.

## When to Activate
Activate when the user asks to:
- format this as JSON
- convert to table
- structure this data

## Core Workflows

Prompt: `Convert the following into {format}: {data}. Return only the formatted output.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
