---
name: marketing-keyword-research
description: Find high-value, low-competition keywords for SEO.
---

# SEO Keyword Research Skill

## Purpose
Find high-value, low-competition keywords for SEO.

## When to Activate
Activate when the user asks to:
- keyword research
- SEO keywords
- what to write about
- keyword ideas

## Core Workflows

Use DataForSEO or Moz API, or LLM with market knowledge for keyword suggestions.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
