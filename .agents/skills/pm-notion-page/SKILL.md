---
name: pm-notion-page
description: Create and update pages in Notion workspaces.
---

# Notion Page Creator Skill

## Purpose
Create and update pages in Notion workspaces.

## When to Activate
Activate when the user asks to:
- create Notion page
- add to Notion
- Notion doc

## Core Workflows

POST to Notion API `/v1/pages` with parent database_id and properties.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
