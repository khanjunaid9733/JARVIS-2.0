---
name: productivity-meeting-prep
description: Prepare an agenda, background notes, and key questions for upcoming meetings.
---

# Meeting Prep Generator Skill

## Purpose
Prepare an agenda, background notes, and key questions for upcoming meetings.

## When to Activate
Activate when the user asks to:
- prepare for meeting
- meeting agenda
- meeting prep

## Core Workflows

Fetch calendar event + attendees, research via web, generate structured agenda.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
