---
name: web-wayback-machine
description: Retrieve archived snapshots of any URL from the Wayback Machine.
---

# Wayback Machine Archive Skill

## Purpose
Retrieve archived snapshots of any URL from the Wayback Machine.

## When to Activate
Activate when the user asks to:
- archived version of <url>
- wayback <url>
- old version of site

## Core Workflows

GET `http://archive.org/wayback/available?url=<URL>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
