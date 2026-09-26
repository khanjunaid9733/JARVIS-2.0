---
name: legal-patent-search
description: Search patents related to a technology or idea.
---

# Patent Search Skill

## Purpose
Search patents related to a technology or idea.

## When to Activate
Activate when the user asks to:
- patent search
- prior art
- patent lookup
- IP search

## Core Workflows

GET USPTO API or Google Patents REST API for patent search results.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
