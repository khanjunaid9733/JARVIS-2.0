---
name: browser-popup-handle
description: Automatically detect and dismiss cookie consent and popup dialogs.
---

# Popup Dismisser Skill

## Purpose
Automatically detect and dismiss cookie consent and popup dialogs.

## When to Activate
Activate when the user asks to:
- dismiss popup
- accept cookies
- close dialog
- handle modal

## Core Workflows

Listen for dialog events: `page.on('dialog', lambda d: d.dismiss())`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
