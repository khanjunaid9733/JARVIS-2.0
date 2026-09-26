---
name: writing-seo-optimize
description: Optimize existing content for target keywords.
---

# SEO Content Optimizer Skill

## Purpose
Optimize existing content for target keywords.

## When to Activate
Activate when the user asks to:
- SEO optimize
- optimize for keywords
- improve SEO

## Core Workflows

Prompt: `Rewrite this content to naturally incorporate the keyword '{keyword}' 5-8 times without keyword stuffing.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
