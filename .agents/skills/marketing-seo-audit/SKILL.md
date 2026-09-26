---
name: marketing-seo-audit
description: Audit a website for SEO issues: meta tags, headings, speed, backlinks.
---

# SEO Site Audit Skill

## Purpose
Audit a website for SEO issues: meta tags, headings, speed, backlinks.

## When to Activate
Activate when the user asks to:
- SEO audit
- website SEO check
- SEO issues
- optimize website

## Core Workflows

Fetch page HTML, check: title/meta description length, H1 count, alt tags, canonical tags.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
