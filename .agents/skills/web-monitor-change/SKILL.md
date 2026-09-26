---
name: web-monitor-change
description: Detect and alert when content on a web page changes.
---

# Website Change Monitor Skill

## Purpose
Detect and alert when content on a web page changes.

## When to Activate
Activate when the user asks to:
- monitor <url> for changes
- watch page
- alert if site changes

## Core Workflows

Poll page every N minutes, hash content, compare — emit event on diff.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
