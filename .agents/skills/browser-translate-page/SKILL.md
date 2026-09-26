---
name: browser-translate-page
description: Translate a web page content in-place to any language.
---

# Live Page Translator Skill

## Purpose
Translate a web page content in-place to any language.

## When to Activate
Activate when the user asks to:
- translate page
- page in Spanish
- translate <url> to

## Core Workflows

Extract page text, translate via API, inject translated text back into DOM.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
