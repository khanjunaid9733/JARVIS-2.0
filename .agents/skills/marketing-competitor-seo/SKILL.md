---
name: marketing-competitor-seo
description: Analyze a competitor's SEO strategy and top-ranking keywords.
---

# Competitor SEO Analysis Skill

## Purpose
Analyze a competitor's SEO strategy and top-ranking keywords.

## When to Activate
Activate when the user asks to:
- competitor SEO
- what keywords does <site> rank for
- competitor analysis

## Core Workflows

Use SpyFu or SEMrush API to fetch top organic keywords for competitor domain.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
