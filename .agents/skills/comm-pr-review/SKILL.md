---
name: comm-pr-review
description: Notify team when a pull request is opened, merged, or reviewed.
---

# GitHub PR Notifier Skill

## Purpose
Notify team when a pull request is opened, merged, or reviewed.

## When to Activate
Activate when the user asks to:
- PR notification
- pull request update
- code review alert

## Core Workflows

Use GitHub webhooks + n8n workflow to relay PR events to Slack/Discord.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
