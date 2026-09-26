---
name: browser-rss-to-json
description: Convert any website's content into clean structured JSON.
---

# Web to Structured Data Skill

## Purpose
Convert any website's content into clean structured JSON.

## When to Activate
Activate when the user asks to:
- website to JSON
- convert page to data
- structured web scrape

## Core Workflows

Extract page → parse with LLM prompt → return structured JSON schema.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
