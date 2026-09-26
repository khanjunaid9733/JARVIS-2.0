---
name: web-form-fill
description: Fill and submit HTML forms on websites using Playwright automation.
---

# Web Form Automation Skill

## Purpose
Fill and submit HTML forms on websites using Playwright automation.

## When to Activate
Activate when the user asks to:
- fill form on <url>
- submit form
- log in to <site>

## Core Workflows

Use Playwright: `page.fill('#field', value); page.click('button[type=submit]')`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
