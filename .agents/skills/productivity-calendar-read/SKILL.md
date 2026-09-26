---
name: productivity-calendar-read
description: Read upcoming events from Google Calendar.
---

# Calendar Reader Skill

## Purpose
Read upcoming events from Google Calendar.

## When to Activate
Activate when the user asks to:
- my schedule
- upcoming events
- what's on my calendar
- next meeting

## Core Workflows

GET `/calendar/v3/calendars/primary/events` with timeMin=now, maxResults=10.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
