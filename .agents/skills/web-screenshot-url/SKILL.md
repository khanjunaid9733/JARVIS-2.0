---
name: web-screenshot-url
description: Take a screenshot of any website URL headlessly.
---

# URL Screenshot Skill

## Purpose
Take a screenshot of any website URL headlessly.

## When to Activate
Activate when the user asks to:
- screenshot <url>
- capture website
- render page

## Core Workflows

Use `playwright` or `selenium` headless browser to capture page screenshot.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
