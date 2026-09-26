---
name: web-search
description: Search the web using DuckDuckGo, Bing, or Google APIs.
---

# Web Search Skill

## Purpose
Search the web using DuckDuckGo, Bing, or Google APIs.

## When to Activate
Activate when the user asks to:
- search for
- find online
- google
- look up
- what is

## Core Workflows

Use DuckDuckGo Instant Answer API or SerpAPI. Return title, snippet, URL for top results.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
