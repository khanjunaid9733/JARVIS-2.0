---
name: codegen-html-page
description: Generate complete HTML/CSS pages from descriptions.
---

# HTML Page Generator Skill

## Purpose
Generate complete HTML/CSS pages from descriptions.

## When to Activate
Activate when the user asks to:
- HTML page
- website design
- create webpage
- landing page code

## Core Workflows

Generate: semantic HTML5, responsive CSS, and basic JavaScript for the described page.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
