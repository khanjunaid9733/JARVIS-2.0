---
name: web-link-extractor
description: Extract all hyperlinks from a web page.
---

# Link Extractor Skill

## Purpose
Extract all hyperlinks from a web page.

## When to Activate
Activate when the user asks to:
- extract links from <url>
- find all links on page

## Core Workflows

Fetch HTML, use HTMLParser to collect all `<a href=>` elements.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
