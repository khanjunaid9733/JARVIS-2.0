---
name: comm-calendar-event
description: Create Google Calendar or Outlook events with reminders.
---

# Create Calendar Event Skill

## Purpose
Create Google Calendar or Outlook events with reminders.

## When to Activate
Activate when the user asks to:
- create event
- schedule meeting
- add to calendar

## Core Workflows

Use Google Calendar API: POST to `/calendar/v3/calendars/primary/events`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
