---
name: marketing-market-research
description: Compile a market research report on any industry or niche.
---

# Market Research Report Skill

## Purpose
Compile a market research report on any industry or niche.

## When to Activate
Activate when the user asks to:
- market research
- industry analysis
- market size
- competitive landscape

## Core Workflows

Prompt: `Create a market research report for {industry} covering: market size, trends, key players, opportunities.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
