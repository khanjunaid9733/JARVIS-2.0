---
name: comm-github-issue
description: Create, comment on, or close GitHub issues via API.
---

# GitHub Issue Creator Skill

## Purpose
Create, comment on, or close GitHub issues via API.

## When to Activate
Activate when the user asks to:
- create GitHub issue
- file bug report
- open issue on <repo>

## Core Workflows

POST to `https://api.github.com/repos/<owner>/<repo>/issues`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
