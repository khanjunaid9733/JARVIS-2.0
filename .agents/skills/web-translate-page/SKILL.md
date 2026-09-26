---
name: web-translate-page
description: Fetch a page and translate its content to English or any target language.
---

# Translate Web Page Skill

## Purpose
Fetch a page and translate its content to English or any target language.

## When to Activate
Activate when the user asks to:
- translate <url> to English
- translate this page

## Core Workflows

Fetch page text, send to LibreTranslate API or ModelGateway for translation.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
