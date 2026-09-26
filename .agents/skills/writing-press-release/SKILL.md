---
name: writing-press-release
description: Draft professional press releases for announcements.
---

# Press Release Writer Skill

## Purpose
Draft professional press releases for announcements.

## When to Activate
Activate when the user asks to:
- press release
- announcement
- news release

## Core Workflows

Prompt: `Write a press release announcing {event/product} for {company}. Include dateline, quote, and boilerplate.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
