---
name: web-summarize-article
description: Fetch and summarize any web article or blog post.
---

# Summarize Article Skill

## Purpose
Fetch and summarize any web article or blog post.

## When to Activate
Activate when the user asks to:
- summarize this article
- tldr <url>
- summarize <url>

## Core Workflows

Fetch page text, chunk if large, route through ModelGateway for summarization.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
